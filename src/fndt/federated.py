"""Federated training of the demand forecaster, with or without the incentive engine.

Without incentive: FedAvg (McMahan et al., 2017). Each site joins a round with a
fixed probability and updates are averaged by local sample count.

With incentive: the reward of the paper, R_i = alpha Q_i - beta C_i + gamma P_i, where
  Q_i  relative loss reduction of the site's update on the twin's validation data
       (server-side validation in the spirit of FLTrust, Cao et al., 2021),
  C_i  normalised device energy kappa C D f^2 + p s / r (Yang et al., 2021),
  P_i  exponentially weighted participation record (a simplified reputation;
       Kang et al., 2019 use subjective logic).
Rewards weight the aggregation (n_i * max(R_i, 0)) and are paid out; payment
raises a site's future participation probability with a stated elasticity
(participation = base + elasticity * avg_payment * (1 - base)).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from fndt.config import Scenario
from fndt.forecasting import FEATURE_DIM, local_sgd, mse


@dataclass
class FLLog:
    round_loss: list[list[float]] = field(default_factory=list)  # per retrain, global loss per round
    participants: list[int] = field(default_factory=list)
    rewards: list[np.ndarray] = field(default_factory=list)
    energy_j: float = 0.0
    uplink_updates: int = 0
    payments: np.ndarray | None = None


class FederatedTrainer:
    def __init__(self, scenario: Scenario, n_sites: int, seed: int, incentive: bool):
        fl, inc = scenario.fl, scenario.incentive
        self.fl, self.inc, self.incentive = fl, inc, incentive
        self.S = n_sites
        rng = np.random.default_rng(seed + 7919)  # device parameters, identical for all strategies
        self.cpu_hz = rng.uniform(*fl.cpu_ghz_range, n_sites) * 1e9
        self.uplink_bps = rng.uniform(*fl.uplink_mbps_range, n_sites) * 1e6
        base = np.full(n_sites, 1.0 - fl.base_dropout)
        if fl.dropout_sites:
            base[np.array(fl.dropout_sites)] -= fl.dropout_sites_prob
        self.base_participation = np.clip(base, inc.min_participation, 1.0)
        self.participation = self.base_participation.copy()
        self.p_record = np.ones(n_sites)
        self.pay_avg = np.zeros(n_sites)
        self.free_riders = set(fl.free_rider_sites)
        self.w = np.zeros(FEATURE_DIM)
        self.w[5] = 1.0  # start from the seasonal-naive forecaster
        self.log = FLLog(payments=np.zeros(n_sites))

    def energy(self, n_samples: np.ndarray) -> np.ndarray:
        bits = FEATURE_DIM * 32.0
        comp = self.fl.kappa * self.fl.cycles_per_sample * n_samples * self.fl.local_epochs * self.cpu_hz**2
        comm = self.fl.tx_power_w * bits / self.uplink_bps
        return comp + comm

    def retrain(self, k: int, local_sets, env, val_set) -> np.ndarray:
        """Run the configured FedAvg rounds. local_sets[i] = (X_i, y_i).

        val_set is the twin's synchronised report data: the only data the server holds.
        It scores update quality (incentive arm) and tracks convergence (all arms).
        """
        fl, inc = self.fl, self.inc
        n = np.array([len(y) for _, y in local_sets], dtype=float)
        e_all = self.energy(n)
        e_ref = max(e_all.max(), 1e-12)
        losses = []
        for r in range(fl.rounds):
            joined = env.fl_uniforms[k % len(env.fl_uniforms), r] < self.participation
            joined &= n > 0
            updates = {}
            for i in np.flatnonzero(joined):
                if i in self.free_riders:
                    updates[i] = self.w + 0.1 * env.free_rider_noise[k % len(env.fl_seeds), r, i]
                    continue
                rng = np.random.default_rng(int(env.fl_seeds[k % len(env.fl_seeds)]) + 1000 * r + i)
                X, y = local_sets[i]
                updates[i] = local_sgd(self.w, X, y, fl.local_epochs, fl.lr, fl.batch, rng)
            self.log.participants.append(len(updates))
            self.log.uplink_updates += len(updates)
            self.log.energy_j += float(e_all[list(updates)].sum()) if updates else 0.0
            self.p_record = inc.participation_ewma * self.p_record + (1 - inc.participation_ewma) * joined
            if not updates:
                losses.append(mse(self.w, *val_set))
                continue
            ids = np.array(sorted(updates))
            W = np.stack([updates[i] for i in ids])
            if self.incentive:
                base_loss = max(mse(self.w, *val_set), 1e-12)
                gain = np.array([max(0.0, (base_loss - mse(wi, *val_set)) / base_loss) for wi in W])
                q = gain / gain.max() if gain.max() > 0 else gain
                c = e_all[ids] / e_ref
                p = self.p_record[ids]
                reward = inc.alpha * q - inc.beta * c + inc.gamma * p
                weight = n[ids] * np.maximum(reward, 0.0)
                full = np.zeros(self.S)
                full[ids] = reward
                self.log.rewards.append(full)
                pay = np.zeros(self.S)
                if weight.sum() > 0:
                    pay[ids] = np.maximum(reward, 0.0) / np.maximum(reward, 0.0).max()
                    self.w = (weight[:, None] * W).sum(axis=0) / weight.sum()
                self.log.payments += pay
                self.pay_avg = 0.7 * self.pay_avg + 0.3 * pay
                # Payment can only raise participation towards 1; an unpaid site
                # behaves exactly as it would without the incentive scheme.
                self.participation = np.clip(
                    self.base_participation + inc.elasticity * self.pay_avg * (1.0 - self.base_participation),
                    inc.min_participation,
                    1.0,
                )
            else:
                weight = n[ids]
                self.w = (weight[:, None] * W).sum(axis=0) / weight.sum()
            losses.append(mse(self.w, *val_set))
        self.log.round_loss.append(losses)
        return self.w
