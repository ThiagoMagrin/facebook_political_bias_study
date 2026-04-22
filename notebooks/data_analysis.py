import marimo

__generated_with = "0.17.0"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import seaborn as sns
    import scikit_posthocs as sp
    import scipy.stats as stats
    import scikit_posthocs as sp
    import numpy as np
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import r2_score
    import pingouin as pg
    import matplotlib.lines as mlines
    sns.set_palette("pastel")
    return mlines, mo, np, pd, pg, plt, sns, stats


@app.cell
def _(pd):
    df_aux = pd.read_csv("../data/data_final.csv").drop(columns=["link_text", "link"])
    df_aux
    return (df_aux,)


@app.cell
def _(df_aux):
    rename_dict = {
        "rph_link": "Content Political Bias", 
        "rph_user": "Publisher Political Bias",
        "rph_delta": "Bias Discrepancy",
        "toxicity": "Toxicity",
        "reaction_score": "Reaction Score",
        "consensus_index": "Consensus Index",
    }
    df = df_aux.rename(rename_dict, axis=1)

    def get_orientation(rph):
        if rph >= 0.3:
            return "Right"
        elif rph <= -0.3:
            return "Left"
        else:
            return "Center"

    df["Content Political Bias Category"] = df["Content Political Bias"].apply(get_orientation)
    df["Publisher Politicial Bias Category"] = df["Publisher Political Bias"].apply(get_orientation)
    return (df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""# Data distribution""")
    return


@app.cell(hide_code=True)
def _(df, mo):
    hist_dropdown = mo.ui.dropdown(
        sorted(df.columns),
        value="Content Political Bias",
        label="Column"
    )

    hist_dropdown
    return (hist_dropdown,)


@app.cell(hide_code=True)
def _(df, hist_dropdown, plt, sns):
    plt.rcParams.update({
        'font.size': 40,
        'axes.titlesize': 18,
        'axes.labelsize': 18,
        'xtick.labelsize': 18,
        'ytick.labelsize': 18,
        'figure.titlesize': 18
    })

    cores_metricas = {
        "Reaction Score": "#009E73",
        "Toxicity": "#CC79A7",
        "Bias Discrepancy": "#D55E00",
        "Consensus Index": "#0072B2"
    }

    col_hist = hist_dropdown.value

    # Special handling for political bias columns - show both histogram and bar plot
    if col_hist in ["Content Political Bias", "Publisher Political Bias"]:
        category_column = "Content Political Bias Category" if col_hist == "Content Political Bias" else "Publisher Politicial Bias Category"

        ordem_especifica = ["Left", "Center", "Right"]

        pastel = sns.color_palette("pastel")
        cores_personalizadas = {
            "Left": pastel[3],
            "Center": "lightgrey",
            "Right": pastel[0]
        }

        # First plot: Histogram
        plt.figure(figsize=(15, 6))
        sns.histplot(
            x=col_hist, 
            data=df, 
            bins=25,
            color="skyblue"
        )
        plt.xlabel(col_hist)
        plt.ylabel("Count")
        plt.tight_layout()
        plt.show()

        # Second plot: Bar plot with counts
        counts = df.drop_duplicates(subset=["account_name"])[category_column].value_counts().reindex(ordem_especifica).reset_index()
        counts.columns = [category_column, "Count"]

        plt.figure(figsize=(10, 6))
        barplot = sns.barplot(
            x=category_column,
            y="Count",
            data=counts,
            order=ordem_especifica,
            palette=cores_personalizadas
        )

        # Add count annotations on top of bars
        for i, (_, row_count) in enumerate(counts.iterrows()):
            barplot.text(
                i, 
                row_count["Count"] + max(counts["Count"]) * 0.02, 
                f'{int(row_count["Count"]):,}', 
                ha='center', 
                va='bottom',
                fontsize=8,
                fontweight='bold'
            )

        plt.xlabel(col_hist)
        plt.ylabel("Count")
        plt.tight_layout()
        plt.show()

    else:
        # Original histogram logic for other columns
        plt.figure(figsize=(15, 6))

        if df[col_hist].dtype != "object" or col_hist in ["Economy", "Education", "Health", "Security", "Culture", "Religion", "Desinformation", "Election", "Politics", "Corruption"]:
            desc = df[col_hist].describe().to_frame().T

            sns.histplot(
                x=col_hist, 
                data=df, 
                kde=True,
                color=cores_metricas.get(col_hist, "skyblue"), 
                bins=25
            )

        else:
            ordem_especifica = ["Left", "Center", "Right"]

            counts = df[col_hist].value_counts().reindex(ordem_especifica).reset_index()
            counts.columns = [col_hist, "Count"]

            pastel = sns.color_palette("pastel")
            cores_personalizadas = {
                "Left": pastel[3],
                "Center": "lightgrey",
                "Right": pastel[0]
            }

            sns.barplot(
                x=col_hist,
                data=counts,
                order=ordem_especifica,
                palette=cores_personalizadas
            )
            plt.ylim([0,2500])

        plt.tight_layout()
        plt.show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""# HeatMap""")
    return


@app.cell(hide_code=True)
def _(df, mo):
    all_columns = [col for col in df.columns if col not in ["account_name", "collection_name", "link", "Content Political Bias Category", "Publisher Political Bias Category"]]
    columns_selected = mo.ui.multiselect(all_columns, label="Selected Columns")
    columns_selected
    return (columns_selected,)


@app.cell(hide_code=True)
def _(columns_selected, df, plt, sns):
    if(columns_selected.value != []):
        data_corr = df[columns_selected.value].corr()

        plt.figure(figsize=(9, 7))
        sns.heatmap(
            data_corr,
            cmap="Blues",
            annot=True,
            fmt=".2f"
        )
        plt.title("Correlation Map", fontsize=12)
        plt.show()
    return


@app.cell(hide_code=True)
def _(df, mo):
    boxplot_x_dropdown = mo.ui.dropdown(sorted(df.drop(columns=["account_name", "collection_name",]).columns), value="Content Political Bias", label="X")
    boxplot_y_dropdown = mo.ui.dropdown(sorted(df.drop(columns=["account_name", "collection_name",]).columns), value="Content Political Bias", label="Y")
    hue_dropdown = mo.ui.dropdown(sorted(df.drop(columns=["account_name", "collection_name"]).columns), label="Hue")
    boxplot_legend_pos = mo.ui.dropdown(['upper right', 'upper left', 'lower right', 'lower left', 'center', 'upper center', 'lower center', 'center left', 'center right'], value="upper left", label="Boxplot Legend Position")
    hue_legend_pos = mo.ui.dropdown(['upper right', 'upper left', 'lower right', 'lower left', 'center', 'upper center', 'lower center', 'center left', 'center right'], value="upper right", label="Hue Legend Position")
    mo.hstack([boxplot_x_dropdown, boxplot_y_dropdown, hue_dropdown, boxplot_legend_pos, hue_legend_pos], justify="start")
    return (
        boxplot_legend_pos,
        boxplot_x_dropdown,
        boxplot_y_dropdown,
        hue_dropdown,
        hue_legend_pos,
    )


@app.cell(hide_code=True)
def _(
    boxplot_legend_pos,
    boxplot_x_dropdown,
    boxplot_y_dropdown,
    df,
    hue_dropdown,
    hue_legend_pos,
    mlines,
    pd,
    pg,
    plt,
    sns,
    stats,
):
    plt.rcParams.update({
        'font.size': 14,
        'axes.titlesize': 20,
        'axes.labelsize': 20,
        'xtick.labelsize': 21,
        'ytick.labelsize': 21,
        'legend.fontsize': 16,
        'legend.title_fontsize': 2
    })

    df_box_plot = df.copy()
    col = boxplot_x_dropdown.value
    y_col = boxplot_y_dropdown.value
    new_col = f"{col} (Categorized)"

    def categorize_column(series: pd.Series, name: str) -> pd.Series:
        if name in ["Content Political Bias", "Publisher Political Bias"]:
            bins = [-float("inf"), -0.3, 0.3, float("inf")]
            labels = ["Left", "Center", "Right"]
        else:
            bins = [-float("inf"), 
                    series.quantile(0.25), 
                    series.median(), 
                    series.quantile(0.75), 
                    float("inf")]
            labels = ["Very Low", "Low", "High", "Very High"]
        return pd.cut(series, bins=bins, labels=labels)

    if pd.api.types.is_numeric_dtype(df_box_plot[col]):
        df_box_plot[new_col] = categorize_column(df_box_plot[col], col)
    else:
        df_box_plot[new_col] = df_box_plot[col]

    hue_value = hue_dropdown.value
    if hue_value is not None:
        if pd.api.types.is_numeric_dtype(df_box_plot[hue_value]):
            category_col = f"{hue_value} (Categorized)"
            if category_col not in df_box_plot.columns:
                df_box_plot[category_col] = categorize_column(df_box_plot[hue_value], hue_value)
            hue_dropdown_sp = category_col
        else:
            hue_dropdown_sp = hue_value
    else:
        hue_dropdown_sp = new_col

    results_per_group = {}
    global_p_val = None
    global_test_name = ""

    is_hue_comparison = (hue_dropdown_sp != new_col) and (hue_dropdown_sp is not None)

    print("="*60)
    if is_hue_comparison:
        print(f"ANÁLISE DETALHADA: Comparando '{hue_dropdown_sp}' DENTRO de cada '{new_col}'")

        x_groups = df_box_plot[new_col].unique()
        if hasattr(x_groups, 'sort_values'):
            x_groups = x_groups.sort_values()

        for x_cat in x_groups:
            print("-" * 60)
            print(f"GRUPO DO EIXO X: {x_cat}")

            sub_df = df_box_plot[df_box_plot[new_col] == x_cat].copy()

            if isinstance(sub_df[hue_dropdown_sp].dtype, pd.CategoricalDtype):
                 sub_df[hue_dropdown_sp] = sub_df[hue_dropdown_sp].cat.remove_unused_categories()

            hue_grouped = sub_df.groupby(hue_dropdown_sp, observed=True)
            groups = [g[y_col].dropna().values for _, g in hue_grouped if len(g[y_col].dropna()) > 1]

            test_name = "N/A"
            p_val = 1.0

            if len(groups) > 1:
                levene_res = pg.homoscedasticity(sub_df, dv=y_col, group=hue_dropdown_sp)
                levene_p = levene_res['pval'].values[0]
                min_n = sub_df[hue_dropdown_sp].value_counts().min()

                if min_n >= 30:
                    if levene_p < 0.05:
                        test_name = "Welch ANOVA"
                        omnibus = pg.welch_anova(dv=y_col, between=hue_dropdown_sp, data=sub_df)
                        p_val = omnibus['p-unc'].values[0]
                    else:
                        test_name = "ANOVA"
                        omnibus = pg.anova(dv=y_col, between=hue_dropdown_sp, data=sub_df)
                        p_val = omnibus['p-unc'].values[0]
                else:
                    test_name = "Kruskal-Wallis"
                    omnibus = pg.kruskal(dv=y_col, between=hue_dropdown_sp, data=sub_df)
                    p_val = omnibus['p-unc'].values[0]

                print(f"  > Teste Geral ({test_name}): p-valor = {p_val:.4e}")

                if p_val < 0.05 or True:
                    print(f"  > Diferença significativa encontrada! Rodando Post-Hoc...")

                    posthoc_df = pd.DataFrame()

                    if test_name == "ANOVA":
                        posthoc_df = pg.pairwise_tukey(data=sub_df, dv=y_col, between=hue_dropdown_sp)
                        sig_col = 'p-tukey'

                    elif test_name == "Welch ANOVA":
                        posthoc_df = pg.pairwise_gameshowell(data=sub_df, dv=y_col, between=hue_dropdown_sp)
                        sig_col = 'pval'

                    elif test_name == "Kruskal-Wallis":
                        posthoc_df = pg.pairwise_tests(data=sub_df, dv=y_col, between=hue_dropdown_sp, 
                                                                        parametric=False, padjust='bonf')
                        sig_col = 'p-corr'

                    if not posthoc_df.empty:
                        sig_pairs = posthoc_df[posthoc_df[sig_col] < 0.05]
                        if not sig_pairs.empty:
                            print(f"  > Pares Significativos (p < 0.05):")
                        else:
                            print("    - Nenhuma diferença pareada significativa encontrada após correção.")
                        for _, row in posthoc_df.iterrows():
                            p_print = row[sig_col]
                            print(f"    - {row['A']} vs {row['B']}: p={p_print:.4f}")
                else:
                    print("  > Nenhuma diferença estatística entre os subgrupos.")
            else:
                print("  > Dados insuficientes para teste (menos de 2 grupos com dados).")

            results_per_group[x_cat] = {'p_val': p_val, 'test': test_name}

    else:
        print("ANÁLISE: Comparação entre grupos do Eixo X")
        grouped = df_box_plot.groupby(new_col, observed=True)
        groups = [group[y_col].dropna().values for _, group in grouped if len(group[y_col].dropna()) > 1]

        if len(groups) > 1:
            levene_stat, levene_p = stats.levene(*groups)
            sample_sizes = [len(g) for g in groups]

            if min(sample_sizes) >= 30:
                if levene_p < 0.05:
                    global_test_name = "Welch ANOVA"
                    res = pg.welch_anova(dv=y_col, between=new_col, data=df_box_plot)
                    global_p_val = res['p-unc'][0]
                    posthoc_func = pg.pairwise_gameshowell
                    sig_col = 'pval'
                else:
                    global_test_name = "ANOVA"
                    stat, global_p_val = stats.f_oneway(*groups)
                    posthoc_func = pg.pairwise_tukey
                    sig_col = 'p-tukey'
            else:
                global_test_name = "Kruskal-Wallis"
                stat, global_p_val = stats.kruskal(*groups)
                posthoc_func = None 
                sig_col = 'p-corr'

            print(f"Teste Geral ({global_test_name}): p = {global_p_val:.4e}")

            if global_p_val < 0.05:
                print("Diferenças significativas encontradas. Pares:")
                if global_test_name == "Kruskal-Wallis":
                    ph = pg.pairwise_tests(data=df_box_plot, dv=y_col, between=new_col, parametric=False, padjust='bonf')
                else:
                    ph = posthoc_func(data=df_box_plot, dv=y_col, between=new_col)

                sig_ph = ph[ph[sig_col] < 0.05]
                if not sig_ph.empty:
                    print(sig_ph[['A', 'B', sig_col]])
                else:
                    print("Nenhum par significativo após correção.")
        else:
            global_test_name, global_p_val = "Dados Insuficientes", 1.0

    print("="*60)

    plt.figure(figsize=(10, 8))
    palette = sns.color_palette("crest")

    ax = sns.boxplot(
        x=new_col,
        y=y_col,
        data=df_box_plot,
        hue=hue_dropdown_sp,
        showfliers=False,
        showmeans=True,
        meanprops={
        "marker": "D",
        "markerfacecolor": "black",
        "markeredgecolor": "black",
        "markersize": 6},
        medianprops={"color": "black", "linewidth": 2},
        palette=palette
    )

    mean_line = mlines.Line2D(
        [], [],
        color='black',
        marker='D',
        linestyle='None',
        markerfacecolor='black',
        markeredgecolor='black',
        markersize=6,
        label='Mean'
    )

    median_line = mlines.Line2D(
        [], [],
        color='black',
        linewidth=1.8,
        label='Median'
    )

    handles, labels = ax.get_legend_handles_labels()

    if hue_dropdown_sp != new_col and handles:
        hue_legend = plt.legend(
            handles=handles, 
            labels=labels, 
            title=hue_dropdown_sp, 
            loc=hue_legend_pos.value,
            fontsize=18,
            title_fontsize=16
        )
        ax.add_artist(hue_legend)
        plt.legend(handles=[mean_line, median_line], loc=boxplot_legend_pos.value, fontsize=18)

    else:
        plt.legend(handles=[mean_line, median_line], loc=boxplot_legend_pos.value, fontsize=18)

    plt.xlabel(new_col)
    plt.ylabel(y_col)
    plt.tight_layout()
    plt.show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""# Bias Interaction Heatmap""")
    return


@app.cell(hide_code=True)
def _(mo):
    heatmap_metric = mo.ui.dropdown(
        options=["Toxicity", "Reaction Score", "Consensus Index", "Bias Discrepancy"],
        value="Toxicity",
        label="Select Metric"
    )

    heatmap_mode = mo.ui.radio(
        options=["Categorical (3×3)", "Continuous (10×10)"],
        value="Categorical (3×3)",
        label="Heatmap Mode"
    )

    agg_func = mo.ui.dropdown(
        options=["mean", "median", "count", "std"],
        value="mean",
        label="Aggregation"
    )

    mo.hstack([heatmap_metric, agg_func, heatmap_mode], justify="start")
    return agg_func, heatmap_metric, heatmap_mode


@app.cell(hide_code=True)
def _(agg_func, df, heatmap_metric, heatmap_mode, np, pd, plt, sns):
    plt.rcParams.update({
        'font.size': 14,
        'axes.titlesize': 16,
        'axes.labelsize': 14,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
    })

    metric_col = heatmap_metric.value
    mode = heatmap_mode.value
    agg = agg_func.value

    if mode == "Categorical (3×3)":
        # Use categorical columns for 3x3 heatmap
        pivot_data = df.groupby(
            ["Publisher Politicial Bias Category", "Content Political Bias Category"],
            observed=True
        )[metric_col].agg(agg).unstack()

        # Reorder axes
        order = ["Left", "Center", "Right"]
        pivot_data = pivot_data.reindex(index=order, columns=order)

        x_label = "Publisher Political Bias"
        y_label = "Content Political Bias"

    else:
        # Create bins for 10x10 continuous heatmap
        bins = np.linspace(-1, 1, 11)
        bin_labels = [f"[{bins[i]:.1f}, {bins[i+1]:.1f})" for i in range(10)]

        df_binned = df.copy()
        df_binned["Publisher Bin"] = pd.cut(
            df_binned["Publisher Political Bias"], 
            bins=bins, 
            labels=bin_labels,
            include_lowest=True
        )
        df_binned["Content Bin"] = pd.cut(
            df_binned["Content Political Bias"], 
            bins=bins, 
            labels=bin_labels,
            include_lowest=True
        )

        pivot_data = df_binned.groupby(
            ["Publisher Bin", "Content Bin"],
            observed=True
        )[metric_col].agg(agg).unstack()

        x_label = "Publisher Political Bias (binned)"
        y_label = "Content Political Bias (binned)"

    # Create heatmap
    plt.figure(figsize=(10, 8))
    heatmap_ax = sns.heatmap(
        pivot_data,
        cmap="RdYlBu_r",
        annot=True,
        fmt=".2f" if agg == "mean" else ".0f",
        linewidths=0.5,
        cbar_kws={'label': f"{agg.capitalize()} {metric_col}"}
    )

    plt.xlabel(x_label)
    plt.ylabel(y_label)
    #plt.title(f"{agg.capitalize()} {metric_col} by Political Bias Alignment")

    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)

    plt.tight_layout()
    plt.gca()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""# Topics Probability Box Plot""")
    return


@app.cell(hide_code=True)
def _(df, plt, sns):
    plt.rcParams.update({
        'font.size': 10,
        'axes.titlesize': 16,
        'axes.labelsize': 16,
        'xtick.labelsize': 16,
        'ytick.labelsize': 16,
        'figure.titlesize': 16
    })

    topics = ["Economy", "Education", "Health", "Security", "Culture", "Religion", "Disinformation", "Election", "Politics", "Corruption"]
    sorted_topics = df[topics].sum().sort_values(ascending=False).index
    topic_sums = df[topics].sum().sort_values(ascending=False)

    color_topics = "#8C564B"

    plt.figure(figsize=(12, 6))

    sns.boxplot(
        data=df[sorted_topics],
        color=color_topics,
        medianprops=dict(color="black", linewidth=2)
    )

    plt.ylabel('Probability')
    plt.xlabel('Topics')
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.show()
    return


if __name__ == "__main__":
    app.run()
