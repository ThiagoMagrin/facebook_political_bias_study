# ---------------------------------------------------------------------------
# Rebuttal analysis - Step 8
# Re-fits the FINAL model on progressively cleaner subsets, keeping only
# publishers that shared at least N distinct links (author_links_history).
# That is very nearly, but not exactly, "the links b_p rests on": a handful of
# shared links carry no bias score and so contribute nothing to b_p. At the
# >= 5 cut three publishers (7 posts) are admitted whose b_p in fact rests on
# four links; 07_bp_reliability.py prints the gap at every threshold.
#
# If the results are an artefact of noisy b_p for thin-history publishers, the
# coefficients should drift as the threshold rises.
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

cont <- c("rph_delta","toxicity","reaction_score","content_leaning","content_extremity",
          "publisher_leaning","publisher_extremity","log_total_reactions",
          "log_author_links", TOPICS)

# FINAL, RE and TOPICS come from _common.R, so this fits the same model 04 does
f <- as.formula(paste("ci ~", FINAL, "+", TOPSTR, "+", RE))

out <- list()
# THRESHOLDS comes from thresholds.txt, the same file 07_bp_reliability.py reads
for (thr in THRESHOLDS) {
  sub <- d %>% filter(author_links_history >= thr)
  n <- nrow(sub)
  # the Smithson-Verkuilen transform and the standardisation are recomputed
  # within each subset, so every fit is internally consistent
  ds <- sub %>%
    mutate(ci = (consensus_index * (n - 1) + 0.5) / n) %>%
    mutate(across(all_of(cont), ~ as.numeric(scale(.))))
  cat(sprintf("fitting threshold >= %2d links  (n = %d, publishers = %d)\n",
              thr, n, n_distinct(ds$account_name)))
  m <- glmmTMB(f, data = ds, family = beta_family())
  r2 <- tryCatch(performance::r2(m), error = function(e) NULL)
  # Each subset is standardised on its own SD, so a standardised coefficient is
  # only comparable across columns where that SD holds still. Carry the SD and
  # the raw-unit coefficient (estimate / SD) so the comparison can be made from
  # the CSV instead of by hand outside the pipeline.
  sds <- vapply(cont, function(v) sd(sub[[v]]), numeric(1))
  out[[as.character(thr)]] <- tidy(m, effects = "fixed", conf.int = TRUE) %>%
    mutate(threshold = thr, n_obs = n,
           n_publishers = n_distinct(ds$account_name),
           converged = isTRUE(m$sdr$pdHess),
           R2_marginal = if (!is.null(r2)) as.numeric(r2$R2_marginal) else NA_real_,
           predictor_sd = unname(sds[term]),
           raw_estimate = estimate / unname(sds[term]))
  cat(sprintf("   converged: %s   AIC: %.1f\n", isTRUE(m$sdr$pdHess), AIC(m)))
}

res <- bind_rows(out)
write_csv(res, file.path(root, "rebuttal", "results", "threshold_models.csv"))

key <- c("content_leaning","content_extremity","publisher_leaning",
         "publisher_extremity","rph_delta","toxicity","reaction_score",
         "log_total_reactions","log_author_links")
tab <- res %>% filter(term %in% key) %>%
  mutate(cell = sprintf("%+.3f%s", estimate,
                        ifelse(p.value < .001, "***", ifelse(p.value < .01, "**",
                        ifelse(p.value < .05, "*", ifelse(p.value < .1, ".", "")))))) %>%
  select(term, threshold, cell) %>%
  pivot_wider(names_from = threshold, values_from = cell, names_prefix = ">=") %>%
  arrange(match(term, key))

sink(file.path(root, "rebuttal", "results", "threshold_models.txt"))
cat(strrep("=", 78), "\n  FINAL MODEL RE-FITTED BY MINIMUM SHARING HISTORY\n", strrep("=", 78), "\n", sep = "")
cat("\nColumns are the minimum number of distinct links a publisher must have\n")
cat("shared for its posts to enter the fit.\n\n")
print(as.data.frame(tab), row.names = FALSE)
cat("\nsignif: *** p<.001  ** p<.01  * p<.05  . p<.10 ; predictors standardised within each subset\n")

cat("\n-- the same coefficients in RAW units (estimate / SD within the subset) --\n")
cat("Read these where the standardised columns are not comparable, i.e. where the\n")
cat("predictor's SD moves across subsets (log_author_links, publisher_leaning).\n\n")
raw <- res %>% filter(term %in% key) %>%
  mutate(cell = sprintf("%+.3f", raw_estimate)) %>%
  select(term, threshold, cell) %>%
  pivot_wider(names_from = threshold, values_from = cell, names_prefix = ">=") %>%
  arrange(match(term, key))
print(as.data.frame(raw), row.names = FALSE)
cat("\n")
print(as.data.frame(res %>% distinct(threshold, n_obs, n_publishers, converged, R2_marginal)),
      row.names = FALSE, digits = 4)
sink()

cat("\n")
print(as.data.frame(tab), row.names = FALSE)

# ---------------------------------------------------------------------------
# Figure: b_p reliability and the stability of the estimates under it
# ---------------------------------------------------------------------------
suppressPackageStartupMessages({ library(ggplot2); library(patchwork); library(forcats) })

PAL <- c("#2c7bb6", "#d7191c", "#fdae61", "#1a9641")
theme_set(theme_minimal(base_size = 12) +
  theme(plot.title = element_text(face = "bold", size = 13),
        plot.subtitle = element_text(size = 10, colour = "grey30"),
        panel.grid.minor = element_blank(),
        strip.text = element_text(face = "bold", size = 10),
        legend.position = "bottom"))

rel <- read_csv(file.path(root, "rebuttal", "results", "bp_reliability.csv"),
                show_col_types = FALSE) %>%
  mutate(history_bin = fct_inorder(history_bin))

# Panel (a) leads with the mean absolute shift, not the correlation. r is
# scale-free and flatters short histories -- at 2 links r = 0.85 looks
# reassuring while b_p moves 0.29 on a scale spanning [-1, +1]. The 1-link
# group is the one the reviewer asked about, so it is shown rather than
# dropped, marked for what it is: b_p there is degenerate, not noisy.
rel_ok <- rel %>% filter(!degenerate)
rel_bad <- rel %>% filter(degenerate)
y_top <- max(rel_ok$mean_abs_shift) * 1.35

p7a <- ggplot(rel_ok, aes(x = history_bin, y = mean_abs_shift, group = 1)) +
  geom_col(data = rel_bad, aes(x = history_bin, y = y_top),
           fill = "grey88", width = .85, inherit.aes = FALSE) +
  geom_text(data = rel_bad, aes(x = history_bin, y = y_top / 2,
                                label = "b_p degenerate\n(-1, 0 or +1)\nleave-one-out\nundefined"),
            inherit.aes = FALSE, size = 2.9, colour = "grey25", lineheight = .95) +
  geom_linerange(aes(ymin = median_abs_shift, ymax = mean_abs_shift),
                 colour = "grey70", linewidth = .8) +
  geom_line(colour = PAL[2], linewidth = .9) +
  geom_point(colour = PAL[2], size = 3) +
  geom_point(aes(y = median_abs_shift), colour = "grey55", size = 2, shape = 17) +
  geom_text(aes(label = sprintf("%.3f", mean_abs_shift)), vjust = -1.0, size = 3.1) +
  geom_text(aes(label = sprintf("r = %.3f", r_full_loo), y = y_top * 0.88),
            size = 2.9, colour = PAL[1]) +
  geom_text(aes(label = paste0("n=", n_posts), y = y_top * 0.97),
            size = 2.8, colour = "grey40") +
  scale_y_continuous(limits = c(0, y_top * 1.04), expand = expansion(mult = c(0, 0))) +
  labs(title = "(a) How far b_p moves when one post is removed",
       subtitle = paste("Circles: mean |shift| in b_p, on a scale spanning [-1, +1].",
                        "Triangles: median. The correlation\nr is printed for comparison -",
                        "it is scale-free and so looks reassuring where the shift is large."),
       x = "distinct links in the publisher's sharing history",
       y = "|shift| in b_p when one post is dropped")

KEY <- c(rph_delta = "Bias Discrepancy",
         toxicity = "Toxicity",
         publisher_extremity = "Publisher extremity",
         publisher_leaning = "Publisher leaning",
         content_leaning = "Content leaning",
         content_extremity = "Content extremity")
th <- read_csv(file.path(root, "rebuttal", "results", "threshold_models.csv"),
               show_col_types = FALSE) %>%
  filter(term %in% names(KEY)) %>%
  mutate(term = factor(KEY[term], levels = unname(KEY)),
         sig = p.value < 0.05)

p7b <- ggplot(th, aes(x = factor(threshold), y = estimate, group = 1)) +
  geom_hline(yintercept = 0, linetype = "dashed", colour = "grey55") +
  geom_ribbon(aes(ymin = conf.low, ymax = conf.high), fill = PAL[1], alpha = .15) +
  geom_line(colour = PAL[1], linewidth = .8) +
  geom_point(aes(shape = sig, fill = sig), colour = PAL[1], size = 2.4) +
  facet_wrap(~term, scales = "free_y", ncol = 3) +
  scale_shape_manual(values = c(`TRUE` = 21, `FALSE` = 4), guide = "none") +
  scale_fill_manual(values = c(`TRUE` = PAL[1], `FALSE` = NA), guide = "none") +
  labs(title = "(b) Restricting to publishers with longer histories does not weaken the findings",
       subtitle = paste("final model re-fitted on each subset; 95% CI.",
                        "Crosses mark estimates that are not significant at 5%"),
       x = "minimum distinct links in the publisher's sharing history",
       y = "standardised coefficient")

ggsave(file.path(FIG, "fig7_bp_reliability.png"), p7a / p7b + plot_layout(heights = c(1, 1.5)),
       width = 9, height = 10, dpi = 300, bg = "white")
cat("saved fig7_bp_reliability.png\n")

# Both panels are also written on their own, as in 05_figures.R: the composite
# is what REVIEWER_RESPONSE.md embeds, the single-panel files are what can be
# placed one at a time in the manuscript or the appendix.
ggsave(file.path(FIG, "fig7a_bp_leave_one_out_shift.png"), p7a,
       width = 9, height = 4.5, dpi = 300, bg = "white")
cat("saved fig7a_bp_leave_one_out_shift.png\n")
ggsave(file.path(FIG, "fig7b_threshold_sensitivity.png"), p7b,
       width = 9, height = 6, dpi = 300, bg = "white")
cat("saved fig7b_threshold_sensitivity.png\n")
