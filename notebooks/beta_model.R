library(readr)
library(dplyr)
library(glmmTMB)
library(performance)
library(forcats)
library(ggplot2)
library(broom.mixed)
library(sjPlot)
library(ggrepel)
library(car)

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

dados <- read_csv("../data/data_final.csv")
n <- nrow(dados)
dados <- dados %>%
  mutate(consensus_index_beta = (consensus_index * (n - 1) + 0.5) / n)
vars_para_escalar <- c("rph_link", "rph_user", "rph_delta", "toxicity", "reaction_score", 
                       'Economy', 'Education', 'Health', 'Security', 'Culture', 'Religion', 
                       'Disinformation', 'Election', 'Politics', 'Corruption')
dados_scaled <- dados %>%
  mutate(across(all_of(vars_para_escalar), ~ as.numeric(scale(.))))
formula_beta <- as.formula(
  "consensus_index_beta ~ rph_link + rph_user + rph_delta + toxicity + reaction_score + Economy + Education + Health + Security + Culture + Religion + Disinformation + Election + Politics + Corruption +
  (toxicity|account_name) + (toxicity|collection_name)"
)
modelo <- glmmTMB(formula_beta, data=dados_scaled, family=beta_family())

check_collinearity(modelo)
tab_model(
  modelo, 
  transform = NULL, 
  show.std = TRUE,
  show.stat = TRUE, 
  digits = 3,
  title = "Resultados do Modelo de Regressão Beta Misto",
  dv.labels = "Índice de Consenso"
)

####
effects <- ranef(modelo)$cond$account_name

df_correlation <- data.frame(
  account_name = rownames(effects),
  Intercept = effects$"(Intercept)",
  Slope_Toxicity = effects$"toxicity"
)

cor_test <- cor.test(df_correlation$Intercept, df_correlation$Slope_Toxicity)
r_value <- round(cor_test$estimate, 2)
p_value <- format.pval(cor_test$p.value, eps = .001)

plot_contas <- plot_top_baseline(modelo, group_name = "account_name", N = 10)
print(plot_contas)

nomes_destaque <- plot_contas$data$level
plot_correlation <- ggplot(df_correlation, aes(x = Intercept, y = Slope_Toxicity)) +
  geom_point(alpha = 0.5, color = "dodgerblue4") +
  geom_smooth(method = "lm", color = "firebrick", se = TRUE) +
  geom_hline(yintercept = 0, linetype = "dashed", alpha = 0.3) +
  geom_vline(xintercept = 0, linetype = "dashed", alpha = 0.3) +
  
  labs(
    title = paste0("Pearson correlation: r = ", round(r_value, 2), " (p < 0.001)"),
    x = "Intercept (Account Baseline Consensus)",
    y = "Toxicity Slope (Sensitivity)"
  ) +
  
  theme_minimal() +
  theme(
    plot.title = element_text(size = 14, hjust = 0.5, face = "bold"),
    axis.title = element_text(size = 12)
  ) +
  
  geom_text_repel(
    data = subset(df_correlation, account_name %in% nomes_destaque),
    aes(label = account_name),
    size = 3.5,         
    fontface = "bold",  
    box.padding = 0.5,
    max.overlaps = 20,    
    point.padding = 0.3
  )
print(plot_correlation)

ggsave("../figures/correlation.png", plot = plot_correlation, 
       width = 8, height = 8, dpi = 300, bg = "white")

ggsave("../figures/top_effects.png", plot = plot_contas, 
       width = 8, height = 8, dpi = 300, bg = "white")