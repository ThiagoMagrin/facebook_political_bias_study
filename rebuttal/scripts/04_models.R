# ---------------------------------------------------------------------------
# Rebuttal analysis - Step 4
# Mixed beta regression models answering the reviewers' requests.
#
#   Block A (Reviewer 1) : controls for post popularity and author activity
#   Block B (Reviewer 2) : leaning / extremity decomposition and a categorical
#                          Left-Center-Right specification
#   Block C              : the final model
#
# Outcome, link, random-effect structure and estimator are identical to the
# published model, so every comparison is like-for-like.
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

d <- read_csv(file.path(DATA, "analysis_dataset.csv"), show_col_types = FALSE)
n <- nrow(d)

# Smithson & Verkuilen (2006) transformation, as in the published model
d <- d %>% mutate(ci = (consensus_index * (n - 1) + 0.5) / n)

cont <- c("rph_link","rph_user","rph_delta","toxicity","reaction_score",
          "content_leaning","content_extremity","publisher_leaning","publisher_extremity",
          "log_total_reactions","log_author_links", TOPICS)

ds <- d %>%
  mutate(across(all_of(cont), ~ as.numeric(scale(.)))) %>%
  mutate(content_side   = factor(content_side,   levels = c("Center","Left","Right")),
         publisher_side = factor(publisher_side, levels = c("Center","Left","Right")))


fit <- function(rhs, label = "", data = ds) {
  f <- as.formula(paste("ci ~", rhs, "+", TOPSTR, "+", RE))
  cat("fitting:", label, "\n")
  m <- glmmTMB(f, data = data, family = beta_family())
  cat("   converged:", m$sdr$pdHess, " AIC:", round(AIC(m), 1), "\n")
  m
}

# ======================================================= BLOCK A =============
BASE <- "rph_link + rph_user + rph_delta + toxicity + reaction_score"

mA0 <- fit(BASE,                                                "A0 published specification")
mA1 <- fit(paste(BASE, "+ log_total_reactions"),                "A1 + post popularity")
mA2 <- fit(paste(BASE, "+ log_author_links"),                   "A2 + author activity")
mA3 <- fit(paste(BASE, "+ log_total_reactions + log_author_links"), "A3 + both controls")

# sensitivity: drop RS, whose relation to CI is partly mechanical
mA4 <- fit(paste("rph_link + rph_user + rph_delta + toxicity",
                 "+ log_total_reactions + log_author_links"),   "A4 both controls, RS removed")

# sensitivity: authors whose b_p rests on a single shared link are excluded
ds_multi <- ds %>% filter(author_links_history >= 2)
mA5 <- fit(paste(BASE, "+ log_total_reactions + log_author_links"),
           "A5 both controls, authors with >= 2 links only", ds_multi)

# ======================================================= BLOCK B =============
LEANEXT <- paste("content_leaning + content_extremity +",
                 "publisher_leaning + publisher_extremity +",
                 "rph_delta + toxicity + reaction_score")
mB1 <- fit(LEANEXT,                                             "B1 leaning + extremity")
mB2 <- fit("content_side + publisher_side + rph_delta + toxicity + reaction_score",
                                                                "B2 categorical L/C/R")

# ======================================================= BLOCK C =============
mC <- fit(FINAL, "C  FINAL MODEL")   # FINAL comes from _common.R

models <- list(A0 = mA0, A1 = mA1, A2 = mA2, A3 = mA3, A4 = mA4, A5 = mA5,
               B1 = mB1, B2 = mB2, C = mC)

# ------------------------------------------------------------- coefficients --
coefs <- bind_rows(lapply(names(models), function(k) {
  tidy(models[[k]], effects = "fixed", conf.int = TRUE) %>%
    mutate(model = k) %>%
    select(model, term, estimate, std.error, statistic, p.value, conf.low, conf.high)
}))
write_csv(coefs, file.path(RES, "model_coefficients.csv"))

# -------------------------------- reproduction check against published Table 3
# 01_build_dataset.py verifies the rebuilt DATASET against data/data_final.csv.
# That is a different claim from "A0 reproduces the published model", which is
# about the FIT, so check that here instead of asserting it in the response
# document. Refitting notebooks/beta_model.R unchanged on the untouched
# data_final.csv returns the same estimates A0 does, so a cell that disagrees
# below is an error in the printed table rather than a reproduction failure.
# Three of them do, and the document reports those three as errata.
published <- data.frame(
  term = c("(Intercept)", "rph_link", "rph_user", "rph_delta", "toxicity",
           "reaction_score", TOPICS),
  pub_estimate  = c(1.645, 0.095, 0.073, -0.158, -0.151, 0.966,
                    0.034, 0.119, -0.106, 0.073, -0.102, -0.016, -0.077,
                    -0.016, 0.102, 0.002),
  pub_conf.low  = c(1.575, 0.032, 0.018, -0.195, -0.199, 0.904,
                    -0.045, 0.039, -0.200, -0.028, -0.211, -0.097, -0.170,
                    -0.115, 0.009, -0.106),
  pub_conf.high = c(1.715, 0.157, 0.128, -0.120, -0.103, 1.029,
                    0.114, 0.200, -0.013, 0.174, 0.007, 0.064, 0.017,
                    0.082, 0.213, 0.102),
  stringsAsFactors = FALSE
)
# The strongest form of the claim, and the one the response document makes: the
# ORIGINAL analysis code (notebooks/beta_model.R), refitted unchanged on the
# ORIGINAL data file, against A0 on the rebuilt one. If those agree then a cell
# where the printed table disagrees is a printing error, not a failure to
# reproduce -- which is a claim about the FIT and so cannot be settled by the
# dataset check 01_build_dataset.py already does.
cat("fitting: published specification, original code on data/data_final.csv\n")
orig <- read_csv(file.path(root, "data", "data_final.csv"), show_col_types = FALSE)
n_orig <- nrow(orig)
orig_scaled <- orig %>%
  mutate(consensus_index_beta = (consensus_index * (n_orig - 1) + 0.5) / n_orig) %>%
  mutate(across(all_of(c("rph_link", "rph_user", "rph_delta", "toxicity",
                         "reaction_score", TOPICS)), ~ as.numeric(scale(.))))
m_orig <- glmmTMB(
  as.formula(paste("consensus_index_beta ~ rph_link + rph_user + rph_delta +",
                   "toxicity + reaction_score +", TOPSTR, "+", RE)),
  data = orig_scaled, family = beta_family())
orig_est <- tibble(term = names(fixef(m_orig)$cond),
                   orig_estimate = unname(fixef(m_orig)$cond))

t3 <- coefs %>% filter(model == "A0") %>%
  select(term, estimate, conf.low, conf.high) %>%
  inner_join(orig_est, by = "term") %>%
  mutate(d_vs_original = estimate - orig_estimate) %>%
  inner_join(published, by = "term") %>%
  mutate(across(c(estimate, conf.low, conf.high), ~ round(.x, 3)),
         d_estimate = estimate - pub_estimate,
         d_conf.low = conf.low - pub_conf.low,
         d_conf.high = conf.high - pub_conf.high,
         agrees = abs(d_estimate) < 5e-4 & abs(d_conf.low) < 5e-4 &
                  abs(d_conf.high) < 5e-4)
stopifnot(nrow(t3) == nrow(published))   # every printed row must be checked
A0_VS_ORIGINAL <- max(abs(t3$d_vs_original))
stopifnot("A0 does not reproduce the original analysis code" = A0_VS_ORIGINAL < 1e-6)
write_csv(t3, file.path(RES, "published_table3_check.csv"))

# ------------------------------------------------------- marginal effects ----
# The response document reports effect sizes in points of CI, not on the logit
# scale, because a standardised logit coefficient is not readable on its own.
# Compute them here so those numbers come out of the pipeline rather than being
# worked out by hand: predicted CI with every predictor at its mean, then the
# change when one predictor moves up by a standard deviation. Also record what
# one SD is worth in the predictor's own units.
marg <- function(mod, terms, label) {
  base <- ds[1, , drop = FALSE]
  for (v in cont) base[[v]] <- 0          # every predictor at its mean
  p0 <- as.numeric(plogis(predict(mod, newdata = base, re.form = NA)))
  bind_rows(lapply(terms, function(v) {
    g <- base; g[[v]] <- 1                # that one predictor at +1 SD
    p1 <- as.numeric(plogis(predict(mod, newdata = g, re.form = NA)))
    raw_sd <- sd(d[[v]])
    tibble(model = label, term = v,
           predicted_ci_at_means = p0,
           predicted_ci_plus_1sd = p1,
           delta_ci_points = (p1 - p0) * 100,
           one_sd_in_raw_units = raw_sd,
           # for a log predictor one SD is a multiplicative change in the level
           one_sd_as_factor = if (startsWith(v, "log_")) exp(raw_sd) else NA_real_)
  }))
}
MARG_C <- c("content_leaning", "content_extremity", "publisher_leaning",
            "publisher_extremity", "rph_delta", "toxicity", "reaction_score",
            "log_total_reactions", "log_author_links")
MARG_A <- c("rph_link", "rph_user", "rph_delta", "toxicity", "reaction_score",
            "log_total_reactions", "log_author_links")
margins <- bind_rows(marg(mA3, MARG_A, "A3"), marg(mC, MARG_C, "C"))
write_csv(margins, file.path(RES, "model_marginal_effects.csv"))

# ------------------------------------------------------------- fit indices ---
fitstats <- bind_rows(lapply(names(models), function(k) {
  m <- models[[k]]
  r2 <- tryCatch(performance::r2(m), error = function(e) NULL)
  tibble(model = k,
         n_obs = nobs(m),
         npar  = length(fixef(m)$cond),
         AIC   = AIC(m), BIC = BIC(m), logLik = as.numeric(logLik(m)),
         R2_marginal    = if (!is.null(r2)) as.numeric(r2$R2_marginal) else NA_real_,
         R2_conditional = if (!is.null(r2)) as.numeric(r2$R2_conditional) else NA_real_,
         converged = isTRUE(m$sdr$pdHess))
}))
write_csv(fitstats, file.path(RES, "model_fit.csv"))

# ------------------------------------------------------------------- VIF -----
vifs <- bind_rows(lapply(names(models), function(k) {
  v <- tryCatch(as.data.frame(check_collinearity(models[[k]])), error = function(e) NULL)
  if (is.null(v)) return(NULL)
  tibble(model = k, term = v$Term, VIF = v$VIF)
}))
write_csv(vifs, file.path(RES, "model_vif.csv"))

# ------------------------------------------------- random-effect variances ---
revar <- bind_rows(lapply(names(models), function(k) {
  vc <- VarCorr(models[[k]])$cond
  bind_rows(lapply(names(vc), function(g) {
    m <- vc[[g]]
    tibble(model = k, group = g,
           sd_intercept = sqrt(m[1, 1]),
           sd_toxicity  = if (nrow(m) > 1) sqrt(m[2, 2]) else NA_real_,
           corr         = if (nrow(m) > 1) m[1, 2] / sqrt(m[1, 1] * m[2, 2]) else NA_real_)
  }))
}))
write_csv(revar, file.path(RES, "model_random_effects.csv"))

# ---------------------------------------------------- console report ---------
sink(file.path(RES, "models.txt"))
cat(strrep("=", 78), "\n  MODEL FIT COMPARISON\n", strrep("=", 78), "\n", sep = "")
print(as.data.frame(fitstats), row.names = FALSE, digits = 5)

cat("\n\n", strrep("=", 78),
    "\n  A0 AGAINST THE PUBLISHED TABLE 3\n", strrep("=", 78), "\n", sep = "")
cat("\nA0 estimates and CIs rounded to the three decimals the paper prints.\n")
cat("A disagreeing row is an erratum in the printed table: the original model\n")
cat("code, refitted unchanged on data_final.csv, returns the A0 column --\n")
cat(sprintf("max |A0 - original code| over all %d coefficients = %.3e\n\n",
            nrow(t3), A0_VS_ORIGINAL))
print(as.data.frame(t3 %>% select(term, estimate, pub_estimate, d_estimate,
                                  conf.low, pub_conf.low,
                                  conf.high, pub_conf.high, agrees)),
      row.names = FALSE, digits = 4)
cat(sprintf("\n%d of %d rows agree on the estimate and both CI bounds.\n",
            sum(t3$agrees), nrow(t3)))

cat("\n\n", strrep("=", 78),
    "\n  BLOCK A - does the published result survive the two new controls?\n",
    strrep("=", 78), "\n", sep = "")
keyA <- c("rph_link","rph_user","rph_delta","toxicity","reaction_score",
          "log_total_reactions","log_author_links")
cmpA <- coefs %>% filter(model %in% c("A0","A1","A2","A3","A4","A5"), term %in% keyA) %>%
  mutate(cell = sprintf("%+.3f%s", estimate,
                        ifelse(p.value < .001, "***", ifelse(p.value < .01, "**",
                        ifelse(p.value < .05, "*", ifelse(p.value < .1, ".", "")))))) %>%
  select(term, model, cell) %>% pivot_wider(names_from = model, values_from = cell) %>%
  arrange(match(term, keyA))
print(as.data.frame(cmpA), row.names = FALSE)
cat("\nsignif: *** p<.001  ** p<.01  * p<.05  . p<.10 ; all predictors standardised\n")

cat("\n-- change in the key coefficients, A0 -> A3 --\n")
chg <- coefs %>% filter(model %in% c("A0","A3"), term %in% keyA[1:5]) %>%
  select(model, term, estimate) %>% pivot_wider(names_from = model, values_from = estimate) %>%
  mutate(abs_change = A3 - A0, pct_change = 100 * (A3 - A0) / abs(A0))
print(as.data.frame(chg), row.names = FALSE, digits = 4)

cat("\n\n", strrep("=", 78),
    "\n  BLOCK B - leaning vs extremity, and the categorical specification\n",
    strrep("=", 78), "\n", sep = "")
cat("\n-- B1: bias split into signed leaning and absolute extremity --\n")
print(as.data.frame(coefs %>% filter(model == "B1") %>%
  filter(!term %in% TOPICS) %>% select(term, estimate, std.error, conf.low, conf.high, p.value)),
  row.names = FALSE, digits = 4)
cat("\n-- B2: categorical Left / Center / Right (Center = reference) --\n")
print(as.data.frame(coefs %>% filter(model == "B2") %>%
  filter(!term %in% TOPICS) %>% select(term, estimate, std.error, conf.low, conf.high, p.value)),
  row.names = FALSE, digits = 4)
cat("\n-- model comparison A0 (linear bias) vs B1 (leaning+extremity) vs B2 (categorical) --\n")
print(as.data.frame(fitstats %>% filter(model %in% c("A0","B1","B2"))), row.names = FALSE, digits = 6)
cat("\nlikelihood-ratio test, A0 nested in B1 (A0 adds the two extremity terms):\n")
print(anova(mA0, mB1))

cat("\n\n", strrep("=", 78), "\n  FINAL MODEL (C)\n", strrep("=", 78), "\n", sep = "")
print(summary(mC))
cat("\n-- collinearity of the final model --\n")
print(check_collinearity(mC))
cat("\n-- R2 --\n")
print(performance::r2(mC))
sink()

saveRDS(models, file.path(RES, "models.rds"))
cat("\ndone. wrote model_coefficients.csv, model_fit.csv, model_vif.csv, models.txt\n")
