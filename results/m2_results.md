# Milestone 2: which factors are real, and how much do they decay?

## Part 1: multiple testing

One-sided tests (returns are signed in the published direction). HLZ is the
Harvey-Liu-Zhu t > 3 hurdle; BY-FDR is Benjamini-Yekutieli at 5%. Original sample
is each factor's in-sample period from the paper that introduced it.

| panel | window | factors | t>1.96 | HLZ t>3 | BY-FDR 5% | HLZ t>3 (NW6) |
|---|---|---|---|---|---|---|
| OSAP op | full sample | 212 | 167 | 130 | 153 | 120 |
| OSAP op | original sample | 212 | 186 | 122 | 150 | 109 |
| OSAP VW | full sample | 179 | 85 | 46 | 55 | 44 |
| OSAP VW | original sample | 179 | 79 | 42 | 45 | 41 |
| JKP US | full sample | 153 | 91 | 68 | 75 | 63 |
| JKP US | original sample | 153 | 81 | 49 | 58 | 46 |

### Replication check: OSAP op original-sample t vs t reported in the paper

| signals | corr | median ours | median paper | share ours > 1.96 |
|---|---|---|---|---|
| 188 | 0.74 | 3.18 | 4.0 | 0.883 |

## Part 2: post-publication decay (McLean and Pontiff 2016)

`r_it = a_i + b1 PostSample_it + b2 PostPub_it + e_it`, factor fixed effects,
standard errors clustered by month. Raw: decay % = b / pooled in-sample mean.
Scaled: each factor's returns divided by its own in-sample mean, so b is the % change.
OSAP op raw is the primary specification. MP columns are McLean and Pontiff's
headline estimates.

| panel | spec | IS mean (%/mo) | b post-sample | t | b post-pub | t  | post-sample % | post-pub % | MP post-sample | MP post-pub | factors | months | obs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| OSAP op | raw | 0.67 | -0.0025 | -3.85 | -0.0037 | -6.49 | -37% | -55% | -26% | -58% | 212 | 1188 | 136338 |
| OSAP op | scaled | 100.0 | -0.2926 | -2.75 | -0.5789 | -6.54 | -29% | -58% | -26% | -58% | 207 | 1188 | 132697 |
| OSAP VW | raw | 0.526 | -0.0023 | -2.77 | -0.0036 | -5.38 | -43% | -68% | -26% | -58% | 179 | 1182 | 116518 |
| OSAP VW | scaled | 100.0 | -0.2826 | -1.55 | -0.7116 | -4.84 | -28% | -71% | -26% | -58% | 129 | 1182 | 85438 |
| JKP US | raw | 0.269 | -0.0002 | -0.39 | -0.0014 | -2.57 | -7% | -53% | -26% | -58% | 153 | 1188 | 108848 |
| JKP US | scaled | 100.0 | -0.1057 | -0.62 | -0.5295 | -2.98 | -11% | -53% | -26% | -58% | 109 | 1188 | 77419 |
| OSAP op to 2013 | raw | 0.67 | -0.0024 | -3.69 | -0.0034 | -4.59 | -36% | -50% | -26% | -58% | 212 | 1056 | 109169 |
| OSAP op to 2013 | scaled | 100.0 | -0.2942 | -2.7 | -0.4838 | -4.21 | -29% | -48% | -26% | -58% | 207 | 1056 | 106056 |

### Dropped factors

- OSAP op (no dates): 0
- OSAP op (scaled: IS mean <= 0 or t < 1): 5 (Activism1, BetaFP, FirmAge, GrSaleToGrOverhead, VarCF)
- OSAP VW (no dates): 0
- OSAP VW (scaled: IS mean <= 0 or t < 1): 50 (AM, AOP, BetaFP, BidAskSpread, BookLeverage, BrandInvest, CashProd, ChNNCOA, ChangeInRecommendation, CompositeDebtIssuance, CoskewACX, DelBreadth, DelCOL, DelDRC, DolVol, EP, EarningsConsistency, EarningsForecastDisparity, ExclExp, FR, FirmAge, Frontier, GrSaleToGrOverhead, Herf, HerfAsset, IntanSP, NetDebtPrice, OrderBacklogChg, PayoutYield, PctAcc, PctTotAcc, PredictedFE, PriceDelayRsq, PriceDelaySlope, PriceDelayTstat, ProbInformedTrading, RD, ReturnSkew, ReturnSkew3F, RevenueSurprise, RoE, ShortInterest, TotalAccruals, VarCF, VolMkt, VolumeTrend, cfp, dVolPut, fgr5yrLag, tang)
- JKP US (no dates): 0
- JKP US (scaled: IS mean <= 0 or t < 1): 44 (age, aliq_at, aliq_mat, ami_126d, at_me, beta_60m, beta_dimson_21d, betabab_1260d, betadown_252d, bidaskhl_21d, cash_at, col_gr1a, corr_1260d, coskew_21d, debt_me, dolvol_var_126d, dsale_drec, dsale_dsga, iskew_capm_21d, iskew_ff3_21d, iskew_hxz4_21d, ivol_capm_252d, kz_index, netdebt_me, ni_ar1, ni_ivol, pi_nix, prc_highprc_252d, rd_sale, ret_3_1, rmax5_21d, rvol_21d, sale_emp_gr1, saleq_gr1, saleq_su, seas_16_20na, sti_gr1a, taccruals_ni, turnover_126d, turnover_var_126d, z_score, zero_trades_126d, zero_trades_21d, zero_trades_252d)

## Comparison with McLean and Pontiff

- Primary (OSAP op): post-publication decay matches closely (-55% raw, -58% scaled vs
  -58%). Post-sample decay is larger in the raw spec (-37% vs -26%) and close in the
  scaled spec (-29%). The raw spec divides pooled coefficients by the pooled in-sample
  mean, so high-mean factors carry more weight; the scaled spec weights factors equally.
- Post-sample window: publication and sample-end dates are year-level (December 31),
  so months in the publication year count as post-sample. McLean and Pontiff use the
  publication month. This likely moves some post-publication months into post-sample.
- Longer sample: cutting OSAP op at 2013 lowers post-publication decay to -50% raw and
  -48% scaled, so 2014 to 2024 adds decay. Our post-publication estimate on the full
  sample is therefore not directly comparable to theirs.
- OSAP VW: decay is larger (-68% raw post-publication). Value-weighted deciles have
  lower in-sample means (0.53%/mo vs 0.67%/mo), and 50 factors fail the scaled-spec
  filter, so that row covers a different factor set.
- JKP US: post-sample decay is small and insignificant (-7% raw, t = -0.39), while
  post-publication decay (-53%) is in line. Likely causes: capped value weighting
  (in-sample mean only 0.27%/mo), and JKP's sample periods and citations, which follow
  Hou-Xue-Zhang replications rather than the original papers.
- Part 1: on original-paper construction, 122 of 212 OSAP signals clear t > 3 in their
  own samples; on value-weighted deciles only 42 of 179 do. The gap is concentrated in
  equal-weighted originals: for those 157 signals the median
  original-sample t falls from 3.43 (op) to 1.62 (VW deciles); for the 22 originally
  value-weighted it is unchanged (2.57 vs 2.54). Source: the doc's `Stock Weight`.
