The main-model coefficients, Table 3, and its reported R2 values remain unchanged.
Apply the following replacements to accompany the updated S5 Appendix.

1. In **Audience reaction metrics**, replace the complete paragraph beginning
   **“Both measures are assigned to each focal post...”** and ending
   **“reaction positivity causes reaction homogeneity.”** with:

```latex
Both measures are assigned to each focal post but are computed from different
sets of reactions. $CRP_i$ summarizes reactions to other posts sharing the
same news link ($j \neq i$), whereas $RHI_i$ uses only reactions to the focal
post $i$. A post with predominantly negative reactions can therefore have a
high $RHI_i$, as can a post with predominantly positive reactions; a roughly
even mix produces a low $RHI_i$. If
$f_i^- = n_i^-/(n_i^+ + n_i^-)$ denotes the focal post's negative-reaction
share, then $RHI_i = |1 - 2f_i^-|$. In this sample, 4,347 posts (94.8\%)
received at least as many positive as negative reactions ($f_i^- \leq 0.5$),
so $RHI_i = 1 - 2f_i^-$ for these observations. Consequently, lower $RHI$
corresponds mathematically to a larger negative-reaction share for the large
majority of posts. The negative-share analyses in \nameref{app:r27_checks}
therefore provide an alternative representation of the same reaction-composition
pattern rather than independent corroborating evidence. Because $CRP_i$
and $RHI_i$ are computed from different posts, no such mathematical identity
holds between them. Their observed correlation ($r \approx 0.75$) should
therefore be interpreted as an empirical association, not as evidence that
reaction positivity causes reaction homogeneity.
```

2. In **Statistical modeling**, replace the two paragraphs from
   **“Total reactions denote the sum of the four reaction types...”** through
   **“commonly used threshold of 5.”** with:

```latex
Total reactions denote the sum of all reaction types recorded for the focal
post, whereas the valence-based measures use only Like, Love, Sad, and Angry.
Page links denote the number of distinct links in the page's full observed
sharing history. To assess the representation of political bias, we compare
models using (i) signed content and page bias alone, (ii) signed bias together
with absolute extremity, and (iii) Left/Center/Right categories in place of
the continuous bias terms.

We separately assess sensitivity by refitting the final mixed beta model
after omitting $CRP$, restricting pages to at least two or five distinct
bias-scored links, restricting posts to the Twitter collection window,
recalculating page bias after excluding all shares of the focal news link
by that page, and applying minimum-reaction cutoffs of 25 and 100 in place
of 50. For the leave-link-out analysis, page leaning, page extremity, and
Bias Discrepancy are recalculated together; observations without remaining
bias-scored history are excluded. The other predictors and the random-effects
structure retain their original definitions. Full details are provided in
\nameref{app:r27_checks}.

All continuous predictors are standardized using Z-score normalization
within each fitted sample, and the boundary adjustment of $RHI$ is recomputed
using that sample's size. Coefficient confidence intervals are two-sided
95\% Wald intervals. Marginal and conditional $R^2$ are calculated using
the Nakagawa method implemented in \texttt{performance::r2\_nakagawa()},
with the lognormal approximation. Potential multicollinearity is assessed
using \texttt{performance::check\_collinearity()}. All VIFs are below 5 in
the main model; the maximum across the sensitivity models is 5.10.
```

3. In **Modeling factors associated with reaction homogeneity**, replace the
   complete paragraph beginning **“Alternative model specifications produced
   substantively consistent results.”** and ending
   **“in \nameref{app:r27_checks}.”** with:

```latex
The specification including signed bias and absolute extremity provided
the best fit among the bias representations considered. Across the final
model and seven sensitivity specifications, the Bias Discrepancy coefficient
remained negative, ranging from $-0.167$ to $-0.219$, with all 95\% confidence
intervals excluding zero. The association persisted when $CRP$ was omitted
($\beta=-0.178$, 95\% CI $[-0.219,-0.138]$) and when page bias was recalculated
without the focal shared link ($\beta=-0.192$, 95\% CI $[-0.234,-0.150]$).
It also persisted under the bias-scored sharing-history restrictions,
restriction to the Twitter collection window, and alternative engagement
cutoffs. Toxicity likewise retained a negative coefficient in all eight
specifications, with all 95\% confidence intervals excluding zero.
Full results are reported in \nameref{app:r27_checks},
Table~\ref{tab:robustness_final}. The negative-reaction-share analyses provide
an alternative representation of the same reaction-composition pattern,
as explained in that appendix.
```

4. In **Conclusion**, replace the complete limitations paragraph beginning
   **“Second, page bias is inferred...”** and ending
   **“a direct measure of latent page ideology.”** with:

```latex
Second, page bias is inferred from the ideologically labeled links observed
in a page's sharing history. Bias Discrepancy therefore measures departure
from the page's observed ideological sharing repertoire, rather than
independently established page ideology or the page's intent in sharing a
particular link. Validation for pages with sufficiently rich sharing histories
showed strong agreement between the inferred page-bias measure and an
independent identity-based classification of page orientation (see
\nameref{app:publisher_validation}). Sensitivity analyses restricted pages
to at least two or five distinct bias-scored links and recalculated page
bias after excluding all shares of the focal link by the page. The negative
association between Bias Discrepancy and reaction homogeneity persisted in
each analysis (see \nameref{app:r27_checks},
Table~\ref{tab:robustness_final}). These checks address short observed
histories and the focal link's contribution to the page-bias estimate, but
they do not establish independently held page ideology. Accordingly, $b_p$
should still be interpreted as a measure of the ideological composition
of a page's observed sharing repertoire.
```

5. In **Conclusion**, replace the complete paragraph beginning
   **“Fifth, the temporal relationship...”** and ending **“private interactions.”**
   with:

```latex
Fifth, the temporal relationship between the Twitter and Facebook data imposes
additional limitations. Content bias scores were estimated from Twitter
retweet behavior between October 1 and December 11, 2018. Of the Facebook
posts in the analytical sample, 4,099 (89.4\%) fall within this window;
222 (4.8\%) precede it, 20 (0.4\%) follow it later in 2018, and 243 (5.3\%)
were published from 2019 to 2022. Restricting the model to the 4,099 posts
within the Twitter window preserved the negative association between Bias
Discrepancy and reaction homogeneity (see \nameref{app:r27_checks}).
Nevertheless, for posts outside this window, $b_c$ is a link-level
ideological proxy estimated from 2018 Twitter circulation rather than a
contemporaneous measure of the link's ideological reception. Because the
Facebook data were collected retrospectively, the sample may also be affected
by survivorship if deleted or otherwise inaccessible posts could not be
observed. CrowdTangle further limits the analysis to the public Facebook
content available through its collection system, excluding private interactions.
```

6. Immediately after that temporal paragraph and before
   **“Finally, toxicity was measured using the Perspective API...”**, insert:

```latex
The engagement criterion also limits generalizability. Although the negative
association between Bias Discrepancy and reaction homogeneity persisted
under minimum-reaction cutoffs of 25 and 100, the main analytical sample
requires at least 50 total reactions and therefore emphasizes higher-engagement
posts. These sensitivity checks do not establish that the same association
holds for low-engagement Facebook posts.
```

Optionally, in the **Abstract**, immediately after
**“In the model, Content Reaction Positivity, Toxicity, and Bias Discrepancy are
among the characteristics most strongly associated with reaction homogeneity.”**,
insert:

```latex
The adjusted negative association between Bias Discrepancy and reaction
homogeneity persisted across sensitivity analyses.
```

Keep the descriptive U-shaped pattern and the adjusted negative coefficient
distinct: the sensitivity analyses concern the adjusted mixed-model association.
