# References used by the simulator (APA 7)

The **Used for** column shows where each source enters the model or the analysis. Where a link is a DOI, it was checked against Crossref. Standards have no DOI and are linked to the publisher's page.

## Standards and architecture

| Reference | Used for |
|---|---|
| International Telecommunication Union. (2022). *Digital twin network – Requirements and architecture* (ITU-T Recommendation Y.3090). https://www.itu.int/rec/T-REC-Y.3090 | Twin accuracy and synchronisation requirements; twin state sync |
| 3rd Generation Partnership Project. (2022). *Study on channel model for frequencies from 0.5 to 100 GHz* (3GPP TR 38.901 V17.0.0). https://www.etsi.org/deliver/etsi_tr/138900_138999/138901/17.00.00_60/tr_138901v170000p.pdf | UMa layout and path loss, shadow fading |
| 3rd Generation Partnership Project. (2022). *E-UTRA; Radio frequency (RF) system scenarios* (3GPP TR 36.942 V17.0.0). https://www.etsi.org/deliver/etsi_tr/136900_136999/136942/17.00.00_60/tr_136942v170000p.pdf | Attenuated, truncated Shannon bound (α = 0.6, −10 dB, 4.4 bps/Hz) |
| 3rd Generation Partnership Project. (2010). *Further advancements for E-UTRA physical layer aspects* (3GPP TR 36.814 V9.0.0). https://www.3gpp.org/ftp/Specs/archive/36_series/36.814/36814-900.zip | BS transmit power (49 dBm / 20 MHz) |
| ITU-R. (2017). *Guidelines for evaluation of radio interface technologies for IMT-2020* (Report ITU-R M.2412-0). https://www.itu.int/pub/R-REP-M.2412 | Carrier frequency, noise figure, thermal noise |
| Polese, M., Bonati, L., D'Oro, S., Basagni, S., & Melodia, T. (2023). Understanding O-RAN: Architecture, interfaces, algorithms, security, and research challenges. *IEEE Communications Surveys & Tutorials, 25*(2), 1376–1411. https://doi.org/10.1109/COMST.2023.3239220 | Non-RT control interval (> 1 s) |

## Traffic, edge computing and queueing

| Reference | Used for |
|---|---|
| Xu, F., Li, Y., Wang, H., Zhang, P., & Jin, D. (2017). Understanding mobile traffic patterns of large scale cellular towers in urban environment. *IEEE/ACM Transactions on Networking, 25*(2), 1147–1161. https://doi.org/10.1109/TNET.2016.2623950 | Land-use diurnal profiles (shapes assumed) |
| Mao, Y., You, C., Zhang, J., Huang, K., & Letaief, K. B. (2017). A survey on mobile edge computing: The communication perspective. *IEEE Communications Surveys & Tutorials, 19*(4), 2322–2358. https://doi.org/10.1109/COMST.2017.2745201 | MEC workload (cycles/bit), offloading latency structure |
| Kleinrock, L. (1975). *Queueing systems, Volume 1: Theory*. Wiley. | M/M/1 sojourn time |
| Kleinrock, L. (1976). *Queueing systems, Volume 2: Computer applications*. Wiley. | Square-root capacity assignment |
| Lindley, D. V. (1952). The theory of queues with a single server. *Mathematical Proceedings of the Cambridge Philosophical Society, 48*(2), 277–289. https://doi.org/10.1017/S0305004100027638 | Lindley-type backlog recursion |

## Federated learning and incentives

| Reference | Used for |
|---|---|
| McMahan, B., Moore, E., Ramage, D., Hampson, S., & Agüera y Arcas, B. (2017). Communication-efficient learning of deep networks from decentralized data. In *Proceedings of AISTATS 2017* (PMLR Vol. 54, pp. 1273–1282). https://proceedings.mlr.press/v54/mcmahan17a.html | FedAvg |
| Yang, Z., Chen, M., Saad, W., Hong, C. S., & Shikh-Bahaei, M. (2021). Energy efficient federated learning over wireless communication networks. *IEEE Transactions on Wireless Communications, 20*(3), 1935–1949. https://doi.org/10.1109/TWC.2020.3037554 | Device energy model, C_i |
| Tran, N. H., Bao, W., Zomaya, A., Nguyen, M. N. H., & Hong, C. S. (2019). Federated learning over wireless networks: Optimization model design and analysis. In *IEEE INFOCOM 2019* (pp. 1387–1395). https://doi.org/10.1109/INFOCOM.2019.8737464 | Device energy model, C_i |
| Cao, X., Fang, M., Liu, J., & Gong, N. Z. (2021). FLTrust: Byzantine-robust federated learning via trust bootstrapping. In *NDSS 2021*. https://doi.org/10.14722/ndss.2021.24434 | Server-side validation for quality, Q_i |
| Kang, J., Xiong, Z., Niyato, D., Xie, S., & Zhang, J. (2019). Incentive mechanism for reliable federated learning: A joint optimization approach to combining reputation and contract theory. *IEEE Internet of Things Journal, 6*(6), 10700–10714. https://doi.org/10.1109/JIOT.2019.2940820 | Reputation-style participation term, P_i |
| Jain, R., Chiu, D.-M., & Hawe, W. R. (1984). *A quantitative measure of fairness and discrimination for resource allocation in shared computer systems* (DEC Research Report TR-301). https://arxiv.org/abs/cs/9809099 | Jain's index |
| Bonawitz, K., Ivanov, V., Kreuter, B., Marcedone, A., McMahan, H. B., Patel, S., Ramage, D., Segal, A., & Seth, K. (2017). Practical secure aggregation for privacy-preserving machine learning. In *ACM CCS 2017* (pp. 1175–1191). https://doi.org/10.1145/3133956.3133982 | Privacy limitation |

## Twin accuracy and statistics

| Reference | Used for |
|---|---|
| Ferriol-Galmés, M., Paillisse, J., Suárez-Varela, J., Rusek, K., Xiao, S., Shi, X., Cheng, X., Barlet-Ros, P., & Cabellos-Aparicio, A. (2023). RouteNet-Fermi: Network modeling with graph neural networks. *IEEE/ACM Transactions on Networking, 31*(6), 3080–3095. https://doi.org/10.1109/TNET.2023.3269983 | Normalised-error fidelity metrics; comparison values |
| Wilcoxon, F. (1945). Individual comparisons by ranking methods. *Biometrics Bulletin, 1*(6), 80–83. https://doi.org/10.2307/3001968 | Paired test |
| Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics, 6*(2), 65–70. https://www.jstor.org/stable/4615733 | Multiplicity correction |
| Efron, B., & Tibshirani, R. J. (1993). *An introduction to the bootstrap*. Chapman & Hall/CRC. https://doi.org/10.1201/9780429246593 | Bootstrap CIs |
| Vargha, A., & Delaney, H. D. (2000). A critique and improvement of the CL common language effect size statistics of McGraw and Wong. *Journal of Educational and Behavioral Statistics, 25*(2), 101–132. https://doi.org/10.3102/10769986025002101 | A12 effect size |
| Demšar, J. (2006). Statistical comparisons of classifiers over multiple data sets. *Journal of Machine Learning Research, 7*, 1–30. https://jmlr.org/papers/v7/demsar06a.html | Friedman ranks |
| Arcuri, A., & Briand, L. (2011). A practical guide for using statistical tests to assess randomized algorithms in software engineering. In *ICSE 2011* (pp. 1–10). https://doi.org/10.1145/1985793.1985795 | Overall test protocol |
| Law, A. M. (2015). *Simulation modeling and analysis* (5th ed.). McGraw-Hill. | Common random numbers |
