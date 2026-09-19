# ---------------------------------------------------------------------------
# Rebuttal analysis - Step 5 : figures
# ---------------------------------------------------------------------------
suppressPackageStartupMessages({
  library(readr); library(dplyr); library(tidyr); library(ggplot2)
  library(forcats); library(scales); library(patchwork)
})

# Shared definitions (repository root, DATA/RES/FIG, TOPICS, RE, FINAL,
# THRESHOLDS) live in _common.R so the four R scripts cannot drift apart.
.rb_a <- commandArgs(trailingOnly = FALSE)
.rb_f <- sub("^--file=", "", .rb_a[grep("^--file=", .rb_a)])
source(file.path(if (length(.rb_f)) dirname(normalizePath(.rb_f[1])) else getwd(),
                 "_common.R"))

# geom_jitter draws from the RNG, so without a seed fig5_face_validity.png is a
# different file on every render and re-running the pipeline produces artefact
# diffs that cannot be told apart from real changes.
set.seed(20260919)

PAL  <- c("#2c7bb6", "#d7191c", "#fdae61", "#1a9641", "#7b3294")
LVLS <- c("Very Low", "Low", "High", "Very High")
PAL4 <- c("Very Low" = "#2c7bb6", "Low" = "#abd9e9",
          "High" = "#fdae61", "Very High" = "#d7191c")

base_theme <- theme_minimal(base_size = 12) +
  theme(plot.title = element_text(face = "bold", size = 13),
        plot.subtitle = element_text(size = 10, colour = "grey30"),
        panel.grid.minor = element_blank(),
        strip.text = element_text(face = "bold"),
        legend.position = "bottom")
theme_set(base_theme)

sv <- function(p, name, w, h) {
  ggsave(file.path(FIG, name), p, width = w, height = h, dpi = 300, bg = "white")
  cat("saved", name, "\n")
}

# ===========================================================================
# FIGURE 1 - composition of reactions and its arithmetic link to consensus
# ===========================================================================
rc <- read_csv(file.path(RES, "fig_reaction_composition.csv"), show_col_types = FALSE)

p1a <- ggplot(rc, aes(x = share_negative)) +
  geom_histogram(binwidth = 0.02, boundary = 0, fill = PAL[1], colour = "white", linewidth = .2) +
  geom_vline(xintercept = 0.5, linetype = "dashed", colour = "grey40") +
  annotate("text", x = 0.02, y = Inf, vjust = 1.6, hjust = 0, size = 3.2, colour = "grey20",
           label = "20.8% of posts\nreceive zero\nSad or Angry") +
  annotate("text", x = 0.52, y = Inf, vjust = 1.6, hjust = 0, size = 3.2, colour = "grey20",
           label = "only 5.2% of posts are\nmajority-negative") +
  scale_x_continuous(labels = percent_format(accuracy = 1)) +
  labs(title = "(a) Most posts receive almost no negative reactions",
       subtitle = expression("negative share  " * f[neg] * " = (Sad+Angry) / (Like+Love+Sad+Angry)"),
       x = expression(f[neg]), y = "posts")

p1b <- ggplot(rc, aes(x = share_negative, y = consensus_index)) +
  geom_point(alpha = 0.18, size = 0.7, colour = PAL[1]) +
  geom_function(fun = function(x) abs(1 - 2 * x), colour = PAL[2], linewidth = 0.9) +
  scale_x_continuous(labels = percent_format(accuracy = 1)) +
  labs(title = "(b) The Consensus Index is a deterministic function of negativity",
       subtitle = expression(CI[i] == group("|", 1 - 2 * f[list(neg, i)], "|") * "  holds exactly for every post"),
       x = expression(f[neg]), y = "Consensus Index")

# binned means rather than a smoother: only 53 posts (1.2%) have RS < 0.4, so a
# loess curve extrapolates the low-RS end from almost no data.
bins <- rc %>%
  # right = FALSE gives left-closed bins [lo, hi), matching 03_descriptives.py.
  # cut()'s default is right-closed, and 170 RS values sit exactly on a decile
  # boundary, so the default made this panel and the text describing it report
  # different counts and means for the same bins.
  mutate(b = cut(reaction_score, breaks = seq(0, 1, 0.1),
                 include.lowest = TRUE, right = FALSE)) %>%
  group_by(b) %>%
  summarise(x = mean(reaction_score), y = mean(consensus_index),
            se = sd(consensus_index) / sqrt(n()), n = n(), .groups = "drop") %>%
  filter(n >= 10)   # the RS < 0.2 range holds a single post; do not draw a line through it

p1c <- ggplot(rc, aes(x = reaction_score, y = consensus_index)) +
  geom_point(alpha = 0.14, size = 0.7, colour = PAL[4]) +
  geom_errorbar(data = bins, aes(x = x, y = y, ymin = y - 1.96 * se, ymax = y + 1.96 * se),
                inherit.aes = FALSE, width = 0.012, colour = PAL[2], linewidth = .6) +
  geom_line(data = bins, aes(x = x, y = y), inherit.aes = FALSE,
            colour = PAL[2], linewidth = .9) +
  geom_point(data = bins, aes(x = x, y = y), inherit.aes = FALSE,
             colour = PAL[2], size = 2.4) +
  geom_text(data = bins, aes(x = x, y = y, label = paste0("n=", n)), inherit.aes = FALSE,
            vjust = 2.3, size = 2.7, colour = "grey30") +
  labs(title = "(c) Against the leave-one-out score the relation is empirical, not definitional",
       subtitle = paste("RS is computed from the other posts sharing the same link (r = 0.746);",
                        "\nred = mean CI within deciles of RS (95% CI); deciles holding fewer than 10 posts omitted"),
       x = "Reaction Score (leave-one-out, content level)", y = "Consensus Index")

sv(p1a / p1b / p1c, "fig1_reaction_composition.png", 8, 12)

# Every panel of a multi-panel figure is also written on its own. The composite
# is what REVIEWER_RESPONSE.md embeds; the single-panel files are what can be
# placed individually in the manuscript or the appendix, where a page carrying
# three stacked panels cannot go. Panel titles keep their "(a)/(b)/(c)" prefix
# so a standalone file stays traceable to the composite it came from.
sv(p1a, "fig1a_negative_share_distribution.png", 8, 4.2)
sv(p1b, "fig1b_consensus_identity.png", 8, 4.2)
sv(p1c, "fig1c_consensus_vs_reaction_score.png", 8, 4.6)

# ===========================================================================
# FIGURE 2 - Block A : the published coefficients under the new controls
# ===========================================================================
co <- read_csv(file.path(RES, "model_coefficients.csv"), show_col_types = FALSE)
lab <- c(rph_link = "Content bias  b_c", rph_user = "Publisher bias  b_p",
         rph_delta = "Bias Discrepancy  \u0394b", toxicity = "Toxicity",
         reaction_score = "Reaction Score",
         log_total_reactions = "log(total reactions)   \u2190 new",
         log_author_links = "log(links shared by author)   \u2190 new")
mlab <- c(A0 = "A0 published", A1 = "A1 + popularity", A2 = "A2 + author activity",
          A3 = "A3 + both", A4 = "A4 + both, RS dropped",
          A5 = "A5 + both, authors >= 2 links")

a <- co %>%
  filter(model %in% names(mlab), term %in% names(lab)) %>%
  mutate(term  = factor(lab[term], levels = rev(unname(lab))),
         model = factor(mlab[model], levels = unname(mlab)),
         sig   = p.value < 0.05)

p2 <- ggplot(a, aes(x = estimate, y = term, colour = model, shape = sig)) +
  geom_vline(xintercept = 0, linetype = "dashed", colour = "grey50") +
  geom_errorbarh(aes(xmin = conf.low, xmax = conf.high), height = 0,
                 position = position_dodge(width = .72), linewidth = .5, alpha = .8) +
  geom_point(size = 2.2, position = position_dodge(width = .72)) +
  scale_shape_manual(values = c(`TRUE` = 16, `FALSE` = 1), guide = "none") +
  scale_colour_manual(values = c("#1f3b73", PAL[1], "#5ab4d6", PAL[3], PAL[2], PAL[4])) +
  guides(colour = guide_legend(nrow = 2, title = NULL)) +
  labs(title = paste0("Adding post popularity and author activity leaves\n",
                      "every published estimate in place"),
       subtitle = "standardised beta, 95% CI; hollow points are not significant at 5%",
       x = "standardised coefficient (logit scale)", y = NULL)
sv(p2, "fig2_controls_comparison.png", 9.5, 7)

# ===========================================================================
# FIGURE 3 - Block B : leaning vs extremity, and the categorical form
# ===========================================================================
lab_b1 <- c(content_leaning = "Content leaning (signed b_c)",
            content_extremity = "Content extremity  |b_c|",
            publisher_leaning = "Publisher leaning (signed b_p)",
            publisher_extremity = "Publisher extremity  |b_p|",
            rph_delta = "Bias Discrepancy  \u0394b",
            toxicity = "Toxicity", reaction_score = "Reaction Score")
b1 <- co %>% filter(model == "B1", term %in% names(lab_b1)) %>%
  mutate(term = factor(lab_b1[term], levels = rev(unname(lab_b1))),
         kind = ifelse(grepl("xtremity", as.character(term)), "extremity", "other"))

p3a <- ggplot(b1, aes(x = estimate, y = term, colour = kind)) +
  geom_vline(xintercept = 0, linetype = "dashed", colour = "grey50") +
  geom_errorbarh(aes(xmin = conf.low, xmax = conf.high), height = .16, linewidth = .5) +
  geom_point(size = 2.6) +
  scale_colour_manual(values = c(extremity = PAL[2], other = PAL[1]), guide = "none") +
  labs(title = "(a) Each bias term split into signed leaning and absolute extremity",
       x = "standardised coefficient", y = NULL)

lab_b2 <- c(content_sideLeft = "Content: Left", content_sideRight = "Content: Right",
            publisher_sideLeft = "Publisher: Left", publisher_sideRight = "Publisher: Right",
            rph_delta = "Bias Discrepancy", toxicity = "Toxicity",
            reaction_score = "Reaction Score")
b2 <- co %>% filter(model == "B2", term %in% names(lab_b2)) %>%
  mutate(term = factor(lab_b2[term], levels = rev(unname(lab_b2))))

p3b <- ggplot(b2, aes(x = estimate, y = term)) +
  geom_vline(xintercept = 0, linetype = "dashed", colour = "grey50") +
  geom_errorbarh(aes(xmin = conf.low, xmax = conf.high), height = .16,
                 linewidth = .5, colour = PAL[4]) +
  geom_point(size = 2.6, colour = PAL[4]) +
  labs(title = "(b) Categorical specification (Center is the reference category)",
       x = "coefficient", y = NULL)

sv(p3a / p3b, "fig3_leaning_extremity.png", 8.5, 8)
sv(p3a, "fig3a_leaning_extremity_split.png", 8.5, 4.2)
sv(p3b, "fig3b_categorical_specification.png", 8.5, 3.9)

# ===========================================================================
# FIGURE 4 - Block Q3 : discrepancy levels and author concentration
# ===========================================================================
fd <- read_csv(file.path(RES, "fig_discrepancy.csv"), show_col_types = FALSE) %>%
  mutate(discrepancy_level = factor(discrepancy_level, levels = LVLS))
tl <- read_csv(file.path(RES, "table_discrepancy_levels.csv"), show_col_types = FALSE) %>%
  mutate(level = factor(level, levels = LVLS))
ac <- read_csv(file.path(RES, "fig_author_concentration.csv"), show_col_types = FALSE) %>%
  mutate(level = factor(level, levels = LVLS))

p4a <- ggplot(fd, aes(x = rph_delta, fill = discrepancy_level)) +
  geom_histogram(binwidth = 0.025, boundary = 0, colour = "white", linewidth = .15) +
  scale_fill_manual(values = PAL4, name = NULL) +
  labs(title = expression("(a) Distribution of Bias Discrepancy " * Delta[b] * ", split at its quartiles"),
       subtitle = "cut points 0.161 / 0.313 / 0.498; n = 1148 / 1148 / 1142 / 1146 posts",
       x = expression(Delta[b]), y = "posts")

p4b <- ggplot(tl, aes(x = level, y = n_authors, fill = level)) +
  geom_col(width = .68) +
  geom_text(aes(label = paste0(n_authors, " authors\n", n_content, " links")),
            vjust = -0.25, size = 3.1) +
  scale_fill_manual(values = PAL4, guide = "none") +
  scale_y_continuous(expand = expansion(mult = c(0, .22))) +
  labs(title = "(b) Each level draws on hundreds of distinct authors",
       x = NULL, y = "distinct authors")

p4c <- ggplot(ac, aes(x = author_frac, y = post_frac, colour = level)) +
  geom_abline(slope = 1, intercept = 0, linetype = "dashed", colour = "grey60") +
  geom_line(linewidth = .9) +
  scale_colour_manual(values = PAL4, name = NULL) +
  scale_x_continuous(labels = percent_format(accuracy = 1)) +
  scale_y_continuous(labels = percent_format(accuracy = 1)) +
  labs(title = "(c) No level is dominated by a handful of authors",
       subtitle = "cumulative share of posts against authors ranked by volume; dashed line = perfect equality",
       x = "authors, ranked from most to least prolific", y = "cumulative share of the level's posts")

# with_ties = FALSE keeps the panel at the eight its title promises (a tie at
# eighth place otherwise returns nine), and account_name breaks the tie the same
# way 03_descriptives.py does, so the figure and the table agree on which pages.
top <- fd %>% count(discrepancy_level, account_name) %>%
  group_by(discrepancy_level) %>% arrange(desc(n), account_name, .by_group = TRUE) %>%
  slice_head(n = 8) %>%
  mutate(share = 100 * n / sum(tl$n_posts[tl$level == first(discrepancy_level)])) %>% ungroup()

p4d <- ggplot(top, aes(x = share, y = reorder_within <- fct_reorder(paste0(account_name, "__", discrepancy_level), share),
                       fill = discrepancy_level)) +
  geom_col(width = .7) +
  facet_wrap(~discrepancy_level, scales = "free_y", ncol = 2) +
  scale_y_discrete(labels = function(x) substr(sub("__.*$", "", x), 1, 34)) +
  scale_fill_manual(values = PAL4, guide = "none") +
  labs(title = "(d) Eight largest contributors within each level",
       x = "share of the level's posts (%)", y = NULL)

sv((p4a / p4b) | (p4c / p4d), "fig4_discrepancy_levels.png", 15, 10)
sv(p4a, "fig4a_discrepancy_distribution.png", 8, 4.2)
sv(p4b, "fig4b_authors_per_level.png", 7.5, 4.6)
sv(p4c, "fig4c_author_concentration.png", 7.5, 5)
sv(p4d, "fig4d_top_contributors.png", 9, 6)

# ===========================================================================
# FIGURE 5 - Q4 face validity
# ===========================================================================
fv <- read_csv(file.path(RES, "fig_face_validity.csv"), show_col_types = FALSE) %>%
  mutate(manual_label = factor(manual_label, levels = c("Left", "Center", "Right")),
         match = manual_label == bp_side)

p5a <- ggplot(fv, aes(x = manual_label, y = bp, colour = manual_label)) +
  annotate("rect", xmin = -Inf, xmax = Inf, ymin = -0.3, ymax = 0.3,
           fill = "grey85", alpha = .55) +
  geom_hline(yintercept = c(-0.3, 0.3), linetype = "dashed", colour = "grey45") +
  geom_boxplot(width = .45, outlier.shape = NA, colour = "grey35", fill = NA) +
  geom_jitter(aes(shape = match), width = .16, height = 0, size = 2.4, alpha = .85) +
  scale_colour_manual(values = c(Left = PAL[1], Center = "grey40", Right = PAL[2]), guide = "none") +
  scale_shape_manual(values = c(`TRUE` = 16, `FALSE` = 4),
                     name = NULL, labels = c(`TRUE` = "agrees", `FALSE` = "disagrees")) +
  labs(title = "(a) Data-driven publisher bias against independent manual coding",
       subtitle = "66 publishers coded by a fixed rule; grey band is the Center range |b_p| < 0.3",
       x = "manual coding", y = "publisher bias  b_p")

p5b <- fv %>% count(manual_label, bp_side) %>%
  mutate(bp_side = factor(bp_side, levels = c("Left", "Center", "Right"))) %>%
  complete(manual_label, bp_side, fill = list(n = 0)) %>%
  ggplot(aes(x = bp_side, y = fct_rev(manual_label), fill = n)) +
  geom_tile(colour = "white", linewidth = 1.5) +
  geom_text(aes(label = n, colour = n > 20), size = 5, fontface = "bold") +
  scale_fill_gradient(low = "#eef3f8", high = PAL[1], guide = "none") +
  scale_colour_manual(values = c(`TRUE` = "white", `FALSE` = "grey20"), guide = "none") +
  labs(title = "(b) Confusion matrix",
       subtitle = "93.9% exact agreement, no Left/Right reversal",
       x = "b_p classified at \u00b10.3", y = "manual coding")

sv(p5a / p5b + plot_layout(heights = c(1.5, 1)), "fig5_face_validity.png", 8, 9)
sv(p5a, "fig5a_bias_vs_manual_coding.png", 8, 5.4)
sv(p5b, "fig5b_confusion_matrix.png", 8, 4.2)

# ===========================================================================
# FIGURE 6 - the final model
# ===========================================================================
lab_c <- c("(Intercept)" = "Intercept",
           content_leaning = "Content leaning (signed)",
           content_extremity = "Content extremity",
           publisher_leaning = "Publisher leaning (signed)",
           publisher_extremity = "Publisher extremity",
           rph_delta = "Bias Discrepancy",
           toxicity = "Toxicity", reaction_score = "Reaction Score",
           log_total_reactions = "log(total reactions)",
           log_author_links = "log(links shared by author)",
           Economy = "Topic: Economy", Education = "Topic: Education",
           Health = "Topic: Health", Security = "Topic: Security",
           Culture = "Topic: Culture", Religion = "Topic: Religion",
           Disinformation = "Topic: Disinformation", Election = "Topic: Election",
           Politics = "Topic: Politics", Corruption = "Topic: Corruption")
cc <- co %>% filter(model == "C", term != "(Intercept)") %>%
  mutate(term  = factor(lab_c[term], levels = rev(unname(lab_c))),
         block = ifelse(grepl("^Topic", term), "topic controls", "focal predictors"),
         sig   = p.value < 0.05)

p6 <- ggplot(cc, aes(x = estimate, y = term, colour = sig)) +
  geom_vline(xintercept = 0, linetype = "dashed", colour = "grey50") +
  geom_errorbarh(aes(xmin = conf.low, xmax = conf.high), height = .15, linewidth = .5) +
  geom_point(size = 2.6) +
  facet_grid(block ~ ., scales = "free_y", space = "free_y") +
  scale_colour_manual(values = c(`TRUE` = PAL[1], `FALSE` = "grey65"), guide = "none") +
  labs(title = "Final model: consensus with every reviewer-requested term included",
       subtitle = paste0("mixed beta GLMM, logit link, standardised predictors\n",
                         "random intercepts and toxicity slopes for publisher and content"),
       x = "standardised coefficient (logit scale), 95% CI", y = NULL)
sv(p6, "fig6_final_model.png", 9, 8.5)

cat("\nall figures written to", FIG, "\n")

# ===========================================================================
# FIGURE 3c - what the leaning/extremity split changes, shown as fitted curves
# ===========================================================================
suppressPackageStartupMessages({ library(glmmTMB) })
models <- readRDS(file.path(RES, "models.rds"))
dd <- read_csv(file.path(root, "rebuttal", "data", "analysis_dataset.csv"), show_col_types = FALSE)
z  <- function(x, ref) (x - mean(ref)) / sd(ref)

grid_base <- function(k) {
  g <- data.frame(rph_link = 0, rph_user = 0, rph_delta = 0, toxicity = 0,
                  reaction_score = 0, log_total_reactions = 0, log_author_links = 0,
                  content_leaning = 0, content_extremity = 0,
                  publisher_leaning = 0, publisher_extremity = 0,
                  account_name = dd$account_name[1], collection_name = dd$collection_name[1])
  for (t in TOPICS) g[[t]] <- 0
  g[rep(1, k), ]
}

curve_for <- function(which_bias) {
  x  <- seq(-1, 1, length.out = 201)
  raw_lin <- if (which_bias == "content") dd$rph_link else dd$rph_user
  raw_ext <- abs(raw_lin)

  gA <- grid_base(length(x))
  if (which_bias == "content") gA$rph_link <- z(x, raw_lin) else gA$rph_user <- z(x, raw_lin)
  yA <- plogis(predict(models$A0, newdata = gA, re.form = NA))

  gC <- grid_base(length(x))
  if (which_bias == "content") {
    gC$content_leaning   <- z(x,        raw_lin)
    gC$content_extremity <- z(abs(x),   raw_ext)
  } else {
    gC$publisher_leaning   <- z(x,      raw_lin)
    gC$publisher_extremity <- z(abs(x), raw_ext)
  }
  yC <- plogis(predict(models$C, newdata = gC, re.form = NA))

  rbind(
    data.frame(bias = x, fit = yA, spec = "published: single linear term",
               panel = which_bias),
    data.frame(bias = x, fit = yC, spec = "re-specified: leaning + extremity",
               panel = which_bias))
}

cv <- rbind(curve_for("content"), curve_for("publisher"))
cv$panel <- factor(cv$panel, levels = c("content", "publisher"),
                   labels = c("Content bias  b_c", "Publisher bias  b_p"))

p3c <- ggplot(cv, aes(x = bias, y = fit, colour = spec, linetype = spec)) +
  geom_vline(xintercept = 0, colour = "grey75") +
  geom_line(linewidth = 1) +
  facet_wrap(~panel) +
  scale_colour_manual(values = c(PAL[1], PAL[2]), name = NULL) +
  scale_linetype_manual(values = c("22", "solid"), name = NULL) +
  labs(title = "(c) A unit of bias does not mean the same thing everywhere",
       subtitle = paste("fitted Consensus Index with every other predictor held at its mean;",
                        "population-level prediction"),
       x = "political bias", y = "predicted Consensus Index")
sv(p3c, "fig3c_partial_effects.png", 9, 4.2)
sv(p3a / p3b / p3c, "fig3_leaning_extremity.png", 8.5, 11)
cat("done\n")
