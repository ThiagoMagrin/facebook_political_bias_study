# ---------------------------------------------------------------------------
# Rebuttal analysis - Step 9  (reviewer R2.8)
# Refits the analysis with the reviewer's proposed outcome: the reaction
# negativity of the target post itself, instead of the Consensus Index.
#
#   D1  beta GLMM on f_neg (Smithson-Verkuilen transformed) - directly
#       comparable to the published CI model
#   D2  D1 plus the leave-one-out content score, to see whether that construct
#       still carries anything once the outcome is negativity itself
#   D3  beta-binomial GLMM on the raw counts cbind(n_neg, n_pos) - the most
#       natural model for this outcome, weighting posts by reaction volume
# ---------------------------------------------------------------------------
suppressPackageStartupMessages({
  library(readr); library(dplyr); library(tidyr); library(glmmTMB)
  library(performance); library(broom.mixed)
})

# Shared definitions (repository root, DATA/RES/FIG, TOPICS, RE, FINAL,
# THRESHOLDS) live in _common.R so the four R scripts cannot drift apart.
.rb_a <- commandArgs(trailingOnly = FALSE)
.rb_f <- sub("^--file=", "", .rb_a[grep("^--file=", .rb_a)])
source(file.path(if (length(.rb_f)) dirname(normalizePath(.rb_f[1])) else getwd(),
                 "_common.R"))
d <- read_csv(file.path(root, "rebuttal", "data", "analysis_dataset.csv"),
              show_col_types = FALSE)
n <- nrow(d)

cont <- c("rph_delta","toxicity","reaction_score","content_leaning","content_extremity",
          "publisher_leaning","publisher_extremity","log_total_reactions",
          "log_author_links", TOPICS)

ds <- d %>%
  mutate(ci    = (consensus_index * (n - 1) + 0.5) / n,
         fneg  = (share_negative  * (n - 1) + 0.5) / n) %>%
  mutate(across(all_of(cont), ~ as.numeric(scale(.))))

# Derived from FINAL, never retyped: D1 and D3 are the final model with the
# leave-one-out score taken out, and mC/D2 put it back. Retyping the terms here
# let 09 keep fitting an old specification after FINAL changed, which is exactly
# what _common.R exists to prevent. The stopifnot fails loudly if FINAL is ever
# restructured so that reaction_score is no longer one of its terms.
.final_terms <- trimws(strsplit(FINAL, "\\+")[[1]])
stopifnot("reaction_score" %in% .final_terms)
FINAL_NO_RS <- paste(setdiff(.final_terms, "reaction_score"), collapse = " + ")
RHS <- paste(FINAL_NO_RS, "+", TOPSTR)   # TOPSTR and RE come from _common.R

fit <- function(lhs, rhs, fam, label) {
  cat("fitting:", label, "\n")
  m <- glmmTMB(as.formula(paste(lhs, "~", rhs, "+", RE)), data = ds, family = fam)
  cat("   converged:", m$sdr$pdHess, "  AIC:", round(AIC(m), 1), "\n")
  m
}

# performance::r2() decomposes the variance against an intercept-only model, and
# it refits one itself by re-evaluating the fitted model's stored call. That call
# carries `family = fam` -- a variable here, because D3 needs a different family
# from D1 and D2 -- and `fam` is not resolvable where insight::null_model()
# evaluates it. The refit then fails, and r2() does not error: it falls back to a
# decomposition that returns a conditional R2 of exactly 1. 04_models.R escapes
# this only because it happens to write `family = beta_family()` as a literal, so
# the same model C comes back as 0.977 there and as 1.000 here.
#
# That silent failure is what made an earlier version of this script report no R2
# at all and assert in a comment that the values were degenerate. They are not:
# fitting the null model here and passing it explicitly -- which is exactly what
# the warning asks for -- returns the real decomposition. The stopifnot keeps the
# failure loud if the null fit ever stops converging.
null_fit <- function(lhs, fam, label) {
  cat("fitting null model for:", label, "\n")
  m0 <- glmmTMB(as.formula(paste(lhs, "~ 1 +", RE)), data = ds, family = fam)
  stopifnot("null model did not converge; r2 would be silently wrong" =
              isTRUE(m0$sdr$pdHess))
  m0
}

# C_ref: the document's final model, refitted here so the two outcomes are
# compared on exactly the same right-hand side
mC  <- fit("ci",   paste(RHS, "+ reaction_score"), beta_family(),  "C  consensus index (reference)")
mD1 <- fit("fneg", RHS,                            beta_family(),  "D1 reaction negativity")
mD2 <- fit("fneg", paste(RHS, "+ reaction_score"), beta_family(),  "D2 reaction negativity + LOO score")
mD3 <- fit("cbind(negative_reactions, positive_reactions)", RHS,
           betabinomial(), "D3 reaction negativity, beta-binomial on counts")

models <- list(C = mC, D1 = mD1, D2 = mD2, D3 = mD3)

nulls <- list(
  C  = null_fit("ci",   beta_family(),  "C"),
  D1 = null_fit("fneg", beta_family(),  "D1"),
  D2 = null_fit("fneg", beta_family(),  "D2"),
  D3 = null_fit("cbind(negative_reactions, positive_reactions)",
                betabinomial(), "D3")
)
stopifnot(identical(names(models), names(nulls)))

coefs <- bind_rows(lapply(names(models), function(k)
  tidy(models[[k]], effects = "fixed", conf.int = TRUE) %>% mutate(model = k)))
write_csv(coefs, file.path(RES, "negativity_models.csv"))

# R2 is computed against the explicit null models above, never against the one
# r2() would try to refit on its own. The values carry the section 4.1 argument
# directly: adding the leave-one-out score to D1 raises the MARGINAL R2 while the
# CONDITIONAL R2 falls, i.e. variance crosses the fixed/random boundary rather
# than being newly explained.
#
# AIC and R2 alike are comparable only within an outcome (D1 vs D2), never
# across outcomes (C vs D1) - different response variables.
fitstats <- bind_rows(lapply(names(models), function(k) {
  m <- models[[k]]
  r2 <- tryCatch(performance::r2_nakagawa(m, null_model = nulls[[k]]),
                 error = function(e) NULL)
  tibble(model = k, outcome = if (k == "C") "Consensus Index" else "reaction negativity",
         family = if (k == "D3") "beta-binomial" else "beta",
         AIC = AIC(m), logLik = as.numeric(logLik(m)),
         converged = isTRUE(m$sdr$pdHess),
         R2_marginal    = if (!is.null(r2)) as.numeric(r2$R2_marginal) else NA_real_,
         R2_conditional = if (!is.null(r2)) as.numeric(r2$R2_conditional) else NA_real_)
}))
write_csv(fitstats, file.path(RES, "negativity_fit.csv"))

# random-effect SDs: these show where the content-level variance sits, and
# whether the leave-one-out score is competing with the content intercept
revar <- bind_rows(lapply(names(models), function(k) {
  vc <- VarCorr(models[[k]])$cond
  bind_rows(lapply(names(vc), function(g) {
    mm <- vc[[g]]
    tibble(model = k, group = g, sd_intercept = sqrt(mm[1, 1]),
           sd_toxicity = if (nrow(mm) > 1) sqrt(mm[2, 2]) else NA_real_)
  }))
}))
write_csv(revar, file.path(RES, "negativity_random_effects.csv"))

# A positive-definite Hessian does not rule out a variance component sitting on
# the zero boundary: the two diagnostics answer different questions, and D3's
# publisher toxicity slope does sit there. Flag it from the estimates rather
# than leaving the reader to notice a 0.002 in the table.
SING_TOL <- 0.01
singular <- revar %>%
  filter(sd_intercept < SING_TOL | (!is.na(sd_toxicity) & sd_toxicity < SING_TOL))

KEY <- c("content_leaning","content_extremity","publisher_leaning","publisher_extremity",
         "rph_delta","toxicity","reaction_score","log_total_reactions","log_author_links")
tab <- coefs %>% filter(term %in% KEY) %>%
  mutate(cell = sprintf("%+.3f%s", estimate,
                        ifelse(p.value < .001, "***", ifelse(p.value < .01, "**",
                        ifelse(p.value < .05, "*", ifelse(p.value < .1, ".", "")))))) %>%
  select(term, model, cell) %>% pivot_wider(names_from = model, values_from = cell) %>%
  arrange(match(term, KEY))

sink(file.path(RES, "negativity_models.txt"))
cat(strrep("=", 78), "\n  R2.8 - REACTION NEGATIVITY AS THE OUTCOME\n", strrep("=", 78), "\n", sep = "")
cat("\nC  = Consensus Index (published outcome)\n")
cat("D1 = reaction negativity of the target post\n")
cat("D2 = D1 plus the leave-one-out content score\n")
cat("D3 = reaction negativity, beta-binomial on raw counts\n\n")
cat("NOTE: CI is high when reactions are homogeneous; negativity is high when they\n")
cat("are hostile. Because CI = |1 - 2*f_neg|, a predictor that lowers consensus by\n")
cat("raising negativity flips sign between the two columns. Signs are EXPECTED to\n")
cat("be opposite.\n\n")
print(as.data.frame(tab), row.names = FALSE)
cat("\nsignif: *** p<.001  ** p<.01  * p<.05  . p<.10\n\n")
print(as.data.frame(fitstats), row.names = FALSE, digits = 7)
cat("\nAIC is comparable only within an outcome. C uses a different response\n")
cat("variable from D1-D3, so C's AIC must not be compared with theirs.\n")
cat("\n-- random-effect SDs --\n")
print(as.data.frame(revar), row.names = FALSE, digits = 4)
cat("\nIf the leave-one-out score were adding information beyond content identity,\n")
cat("the content intercept SD would not change much when it is added. Compare\n")
cat("D1 (no score) with D2 (score added).\n")

cat("\n-- variance components at the zero boundary (|sd| <", SING_TOL, ") --\n")
if (nrow(singular) == 0) {
  cat("none: every random-effect SD is away from zero.\n")
} else {
  print(as.data.frame(singular), row.names = FALSE, digits = 4)
  cat("\nThese fits converged with a positive-definite Hessian AND carry a variance\n")
  cat("component estimated at zero; the two are not in conflict. The fixed effects\n")
  cat("remain interpretable, but the random-effect structure is over-specified for\n")
  cat("this outcome and the corresponding random slope should not be interpreted.\n")
}
cat("\n\n-- D1 in full --\n")
print(as.data.frame(coefs %>% filter(model == "D1") %>%
  select(term, estimate, std.error, conf.low, conf.high, p.value)), row.names = FALSE, digits = 4)
sink()

cat("\n"); print(as.data.frame(tab), row.names = FALSE)

# ---------------------------------------------------------------------------
# Figure: the two outcomes side by side, and where the content variance sits
# ---------------------------------------------------------------------------
suppressPackageStartupMessages({ library(ggplot2); library(forcats); library(patchwork) })
PAL <- c("#2c7bb6", "#d7191c", "#fdae61", "#1a9641")
theme_set(theme_minimal(base_size = 12) +
  theme(plot.title = element_text(face = "bold", size = 13),
        plot.subtitle = element_text(size = 10, colour = "grey30"),
        panel.grid.minor = element_blank(), legend.position = "bottom",
        strip.text = element_text(face = "bold")))

co <- read_csv(file.path(RES, "negativity_models.csv"), show_col_types = FALSE)
KEY <- c(rph_delta = "Bias Discrepancy", toxicity = "Toxicity",
         content_leaning = "Content leaning", content_extremity = "Content extremity",
         publisher_leaning = "Publisher leaning", publisher_extremity = "Publisher extremity",
         log_total_reactions = "log(total reactions)")
MOD <- c(C = "C · outcome = Consensus Index", D1 = "D1 · outcome = reaction negativity",
         D3 = "D3 · reaction negativity, beta-binomial")

a <- co %>% filter(model %in% names(MOD), term %in% names(KEY)) %>%
  mutate(term = factor(KEY[term], levels = rev(unname(KEY))),
         model = factor(MOD[model], levels = unname(MOD)), sig = p.value < 0.05)

p8a <- ggplot(a, aes(x = estimate, y = term, colour = model, shape = sig)) +
  geom_vline(xintercept = 0, linetype = "dashed", colour = "grey50") +
  geom_errorbarh(aes(xmin = conf.low, xmax = conf.high), height = 0,
                 position = position_dodge(width = .68), linewidth = .5, alpha = .85) +
  geom_point(size = 2.4, position = position_dodge(width = .68)) +
  scale_shape_manual(values = c(`TRUE` = 16, `FALSE` = 1), guide = "none") +
  scale_colour_manual(values = c(PAL[1], PAL[2], PAL[4]), name = NULL) +
  guides(colour = guide_legend(nrow = 3)) +
  labs(title = "(a) The same data re-expressed, not an independent confirmation",
       subtitle = paste("CI = |1 - 2 x f_neg| exactly, so agreement between the two outcomes is arithmetic, not evidence.",
                        "\nThe signs are expected to be opposite. Hollow points are not significant at 5%."),
       x = "standardised coefficient", y = NULL)

# Panel (b) must show a matched pair (same outcome, same family, score in vs
# out) for every outcome it claims. The consensus pair lives in script 04's
# output, so it is pulled in here rather than leaving the claim unsupported.
re_neg <- read_csv(file.path(RES, "negativity_random_effects.csv"), show_col_types = FALSE)
re_con <- read_csv(file.path(RES, "model_random_effects.csv"), show_col_types = FALSE) %>%
  filter(model %in% c("A3", "A4"))

re <- bind_rows(
  re_con %>% filter(group == "collection_name") %>%
    transmute(sd_intercept, outcome = "outcome: Consensus Index",
              has_rs = model == "A3",
              lab = ifelse(model == "A3", "A3\nscore in", "A4\nscore out")),
  re_neg %>% filter(group == "collection_name", model %in% c("D1", "D2")) %>%
    transmute(sd_intercept, outcome = "outcome: reaction negativity",
              has_rs = model == "D2",
              lab = ifelse(model == "D2", "D2\nscore in", "D1\nscore out"))
) %>% mutate(lab = fct_inorder(lab))

p8b <- ggplot(re, aes(x = lab, y = sd_intercept, fill = has_rs)) +
  geom_col(width = .6) +
  geom_text(aes(label = sprintf("%.3f", sd_intercept)), vjust = -0.4, size = 3.6) +
  facet_wrap(~outcome, scales = "free_x") +
  scale_fill_manual(values = c(`TRUE` = PAL[1], `FALSE` = PAL[2]), name = NULL,
                    labels = c(`TRUE` = "leave-one-out score in the model",
                               `FALSE` = "score removed")) +
  scale_y_continuous(expand = expansion(mult = c(0, .2))) +
  labs(title = "(b) The leave-one-out score competes with the content random intercept",
       subtitle = paste("SD of the content random intercept. Each panel is a matched pair -",
                        "same outcome and\nsame model family, score in versus out.",
                        "Removing it roughly doubles the intercept."),
       x = NULL, y = "SD of content random intercept")

ggsave(file.path(FIG, "fig8_negativity_outcome.png"), p8a / p8b + plot_layout(heights = c(1.25, 1)),
       width = 9, height = 9.5, dpi = 300, bg = "white")
cat("saved fig8_negativity_outcome.png\n")

# Both panels are also written on their own, as in 05_figures.R: the composite
# is what REVIEWER_RESPONSE.md embeds, the single-panel files are what can be
# placed one at a time in the manuscript or the appendix.
ggsave(file.path(FIG, "fig8a_negativity_coefficients.png"), p8a,
       width = 9, height = 5.3, dpi = 300, bg = "white")
cat("saved fig8a_negativity_coefficients.png\n")
ggsave(file.path(FIG, "fig8b_content_random_intercept.png"), p8b,
       width = 9, height = 4.4, dpi = 300, bg = "white")
cat("saved fig8b_content_random_intercept.png\n")
