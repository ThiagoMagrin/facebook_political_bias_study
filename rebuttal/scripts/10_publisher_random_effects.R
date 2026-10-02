# ---------------------------------------------------------------------------
# Rebuttal analysis - Step 10 : publisher random effects (manuscript Fig 6)
#
# Saves top_effects.png (Fig 6a) and correlation.png (Fig 6b) in figures/model_C/
# from the final model C, the model of the manuscript's main table. The
# originals remain in figures/ and come from notebooks/beta_model.R, i.e. the
# published specification (A0). Nothing is refitted: the models are read from
# models.rds as written by 04_models.R.
#
# The plotting code is the one in notebooks/beta_model.R, so the figures change
# only in what they show, not in how they look.
#
# Two different numbers are both called "the intercept-slope correlation":
#   * the Pearson r between the predicted (conditional-mode) intercepts and
#     slopes of the 1,243 publishers -- what Fig 6b plots and its title reports;
#   * rho01, the correlation parameter estimated by the model -- what the
#     random-effects block of the main table reports.
# They are not the same quantity and need not agree, so both are written out.
# ---------------------------------------------------------------------------
suppressPackageStartupMessages({
  library(readr); library(dplyr); library(glmmTMB); library(ggplot2)
  library(broom.mixed); library(ggrepel)
})

# Shared definitions (repository root, DATA/RES/FIG, TOPICS, RE, FINAL,
# THRESHOLDS) live in _common.R so the R scripts cannot drift apart.
.rb_a <- commandArgs(trailingOnly = FALSE)
.rb_f <- sub("^--file=", "", .rb_a[grep("^--file=", .rb_a)])
source(file.path(if (length(.rb_f)) dirname(normalizePath(.rb_f[1])) else getwd(),
                 "_common.R"))

MS_FIG <- file.path(root, "figures", "model_C")  # model C versions of manuscript Fig 6
GROUP  <- "account_name"                        # publishers; collection_name is content
N_TOP  <- 10                                    # as in notebooks/beta_model.R
dir.create(MS_FIG, showWarnings = FALSE, recursive = TRUE)

models <- readRDS(file.path(RES, "models.rds"))
models <- lapply(models, function(m) tryCatch(up2date(m), error = function(e) m))
mC <- models$C

# the model in models.rds must still be the one FINAL describes
stopifnot("models$C is not the FINAL specification in _common.R" =
  setequal(names(fixef(mC)$cond),
           c("(Intercept)", trimws(strsplit(FINAL, "+", fixed = TRUE)[[1]]), TOPICS)))

# ------------------------------------------------- random effects per model --
publisher_re <- function(mod) {
  vals <- broom.mixed::tidy(mod, effects = "ran_vals") %>% filter(group == GROUP)
  inner_join(
    vals %>% filter(term == "(Intercept)") %>%
      select(account_name = level, Intercept = estimate, se_intercept = std.error),
    vals %>% filter(term == "toxicity") %>%
      select(account_name = level, Slope_Toxicity = estimate, se_slope = std.error),
    by = "account_name") %>%
    mutate(account_name = as.character(account_name),
           rank_high = rank(-Intercept, ties.method = "first"),
           rank_low  = rank(Intercept, ties.method = "first"),
           rank_abs  = rank(-abs(Intercept), ties.method = "first"))
}

rho01 <- function(mod) {
  v <- VarCorr(mod)$cond[[GROUP]]
  v[1, 2] / sqrt(v[1, 1] * v[2, 2])
}

re_C  <- publisher_re(mC)
re_A0 <- publisher_re(models$A0)
stopifnot(nrow(re_C) == 1243)

ct <- cor.test(re_C$Intercept, re_C$Slope_Toxicity)
r_value <- unname(ct$estimate)
p_value <- ct$p.value

write_csv(re_C %>% arrange(desc(Intercept)),
          file.path(RES, "publisher_random_effects_C.csv"))

# ------------------------------------------------------------- Fig 6a -------
# notebooks/beta_model.R::plot_top_baseline, unchanged
plot_top_baseline <- function(fitted_model, group_name, N = 20, char_limit = 30) {
  re_data <- broom.mixed::tidy(fitted_model, effects = "ran_vals") %>%
    filter(group == group_name, term == "(Intercept)")

  top_data <- re_data %>%
    mutate(abs_impact = abs(estimate)) %>%
    slice_max(order_by = abs_impact, n = N) %>%
    mutate(
      level = as.character(level),
      level_trunc = ifelse(nchar(level) > char_limit,
                           paste0(substr(level, 1, char_limit - 3), "..."),
                           level)
    )

  ggplot(top_data, aes(x = estimate, y = reorder(level_trunc, estimate))) +
    geom_point(size = 3, color = "#2c7bb6") +
    geom_errorbarh(aes(xmin = estimate - 1.96 * std.error,
                       xmax = estimate + 1.96 * std.error),
                   height = 0.2, alpha = 0.5, color = "#2c7bb6") +
    geom_vline(xintercept = 0, lty = 2, color = "gray30") +
    theme_minimal() +
    theme(
      axis.text.y = element_text(size = 12),
      axis.text.x = element_text(size = 12),
      axis.title.x = element_text(size = 14),
      plot.title = element_text(hjust = 0.5, face = "bold", size = 16),
      panel.grid.minor = element_blank()
    ) +
    labs(y = NULL,
         x = "Estimate (Deviation from Global Mean)",
         title = "Top Baseline Consensus (Intercepts)")
}

plot_contas <- plot_top_baseline(mC, group_name = GROUP, N = N_TOP)
nomes_destaque <- plot_contas$data$level

# ------------------------------------------------------------- Fig 6b -------
p_label <- if (p_value < 0.001) "p < 0.001" else sprintf("p = %.3f", p_value)

plot_correlation <- ggplot(re_C, aes(x = Intercept, y = Slope_Toxicity)) +
  geom_point(alpha = 0.5, color = "dodgerblue4") +
  geom_smooth(method = "lm", formula = y ~ x, color = "firebrick", se = TRUE) +
  geom_hline(yintercept = 0, linetype = "dashed", alpha = 0.3) +
  geom_vline(xintercept = 0, linetype = "dashed", alpha = 0.3) +
  labs(
    title = sprintf("Pearson correlation: r = %.2f (%s)", r_value, p_label),
    x = "Intercept (Account Baseline Consensus)",
    y = "Toxicity Slope (Sensitivity)"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 14, hjust = 0.5, face = "bold"),
    axis.title = element_text(size = 12)
  ) +
  geom_text_repel(
    data = subset(re_C, account_name %in% nomes_destaque),
    aes(label = account_name),
    size = 3.5,
    fontface = "bold",
    box.padding = 0.5,
    max.overlaps = 20,
    point.padding = 0.3,
    seed = 20260919      # label placement is random; fix it so reruns are identical
  )

ggsave(file.path(MS_FIG, "correlation.png"), plot = plot_correlation,
       width = 8, height = 8, dpi = 300, bg = "white")
ggsave(file.path(MS_FIG, "top_effects.png"), plot = plot_contas,
       width = 8, height = 8, dpi = 300, bg = "white")

# ------------------------------------------------------------- report -------
EXAMPLES <- c("UOL Notícias", "Jair M. Bolsonaro")   # the page name has the period

show <- function(x) {
  print(as.data.frame(x %>% transmute(account_name, Intercept = round(Intercept, 3),
                                      se = round(se_intercept, 3),
                                      Slope_Toxicity = round(Slope_Toxicity, 3),
                                      rank_high, rank_low, rank_abs)),
        row.names = FALSE)
}

sink(file.path(RES, "publisher_random_effects.txt"))
cat(strrep("=", 78), "\n  PUBLISHER RANDOM EFFECTS, FINAL MODEL C (manuscript Fig 6)\n",
    strrep("=", 78), "\n", sep = "")
cat(sprintf("\n%d publishers. rank_high = 1 is the highest intercept, rank_low = 1 the lowest,\n",
            nrow(re_C)))
cat("rank_abs = 1 the largest |intercept|. Intercepts are deviations from the global\n")
cat("mean on the logit scale.\n")

cat(sprintf("\n-- Fig 6a: the %d largest |intercept| (what figures/model_C/top_effects.png shows) --\n", N_TOP))
show(re_C %>% filter(rank_abs <= N_TOP) %>% arrange(desc(Intercept)))

cat(sprintf("\n-- the %d highest intercepts (above-average baseline consensus) --\n", N_TOP))
show(re_C %>% filter(rank_high <= N_TOP) %>% arrange(rank_high))

cat(sprintf("\n-- the %d lowest intercepts (below-average baseline consensus) --\n", N_TOP))
show(re_C %>% filter(rank_low <= N_TOP) %>% arrange(rank_low))

cat("\n-- the examples the manuscript text names --\n")
cat("model C:\n");  show(re_C  %>% filter(account_name %in% EXAMPLES))
cat("model A0 (published specification, for comparison):\n")
show(re_A0 %>% filter(account_name %in% EXAMPLES))
cat(sprintf("\nmodel A0, %d largest |intercept|, for comparison:\n", N_TOP))
show(re_A0 %>% filter(rank_abs <= N_TOP) %>% arrange(desc(Intercept)))

cat("\n-- intercept-toxicity slope correlation, publishers --\n")
ct_A0 <- cor.test(re_A0$Intercept, re_A0$Slope_Toxicity)
cat(sprintf("model C : Pearson r of predicted effects = %.4f, 95%% CI [%.4f, %.4f], t(%d) = %.2f, p = %.3g\n",
            r_value, ct$conf.int[1], ct$conf.int[2], as.integer(ct$parameter),
            unname(ct$statistic), p_value))
cat(sprintf("          rho01 estimated by the model     = %.4f\n", rho01(mC)))
cat(sprintf("model A0: Pearson r of predicted effects = %.4f, p = %.3g\n",
            unname(ct_A0$estimate), ct_A0$p.value))
cat(sprintf("          rho01 estimated by the model     = %.4f\n", rho01(models$A0)))
cat("\nFig 6b (figures/model_C/correlation.png) plots, and its title reports, the Pearson r of\n")
cat("the predicted effects. The main table's rho01 row is the model parameter.\n")
sink()

cat("saved figures/model_C/top_effects.png, figures/model_C/correlation.png,",
    "publisher_random_effects.txt, publisher_random_effects_C.csv\n")
