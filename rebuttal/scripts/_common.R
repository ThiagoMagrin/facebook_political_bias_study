# ---------------------------------------------------------------------------
# Shared definitions for the R half of the rebuttal pipeline.
#
# Sourced by 04_models.R, 05_figures.R, 08_threshold_models.R and
# 09_negativity_outcome.R. Everything here used to be copy-pasted into each of
# them: the repository-root resolution, the topic list, the random-effect
# structure and the final model's right-hand side. Editing FINAL in one script
# and not the others left them fitting different models while the response
# document presented them as the same one, with no error to catch it.
# ---------------------------------------------------------------------------

# Repository root, independent of the caller's working directory: PROJECT_ROOT
# if set, otherwise derived from this file's own location (it lives in
# <root>/rebuttal/scripts/).
.rb_common <- (function() {
  for (i in seq_len(sys.nframe())) {
    f <- sys.frame(i)$ofile
    if (!is.null(f)) return(normalizePath(f))
  }
  a <- commandArgs(trailingOnly = FALSE)
  f <- sub("^--file=", "", a[grep("^--file=", a)])
  if (length(f)) normalizePath(f[1]) else NA_character_
})()

root <- Sys.getenv("PROJECT_ROOT", unset = if (!is.na(.rb_common))
  normalizePath(file.path(dirname(.rb_common), "..", "..")) else getwd())
stopifnot(dir.exists(file.path(root, "rebuttal", "data")))

DATA <- file.path(root, "rebuttal", "data")
RES  <- file.path(root, "rebuttal", "results")
FIG  <- file.path(root, "rebuttal", "figures")
dir.create(RES, showWarnings = FALSE, recursive = TRUE)
dir.create(FIG, showWarnings = FALSE, recursive = TRUE)

TOPICS <- c("Economy", "Education", "Health", "Security", "Culture", "Religion",
            "Disinformation", "Election", "Politics", "Corruption")
TOPSTR <- paste(TOPICS, collapse = " + ")

# random-effect structure of the published model, unchanged throughout
RE <- "(toxicity|account_name) + (toxicity|collection_name)"

# the final model's right-hand side (fixed effects other than the topics)
FINAL <- paste("content_leaning + content_extremity + publisher_leaning +",
               "publisher_extremity + rph_delta + toxicity + reaction_score +",
               "log_total_reactions + log_author_links")

# the threshold ladder, shared with 07_bp_reliability.py via thresholds.txt so
# Tables 2.3 and 2.4 cannot describe different subsets
THRESHOLDS <- (function() {
  ln <- readLines(file.path(dirname(.rb_common), "thresholds.txt"), warn = FALSE)
  as.integer(ln[!grepl("^\\s*(#|$)", ln)])
})()
