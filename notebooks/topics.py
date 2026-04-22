import marimo

__generated_with = "0.17.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import polars as pl
    import spacy
    from gensim import corpora
    from gensim.models import LdaMulticore
    from gensim.models import CoherenceModel
    import pyLDAvis
    import pyLDAvis.gensim_models
    import matplotlib.pyplot as plt
    import pandas as pd
    from transformers import pipeline
    from tqdm import tqdm
    from transformers import AutoTokenizer
    import torch
    from tqdm.auto import tqdm
    import re
    import gc
    import traceback
    from huggingface_hub import login
    from transformers import AutoModelForSeq2SeqLM
    from sklearn.metrics import precision_recall_curve, precision_score, recall_score, f1_score
    import numpy as np

    nlp = spacy.load("pt_core_news_sm")
    return (
        AutoModelForSeq2SeqLM,
        AutoTokenizer,
        CoherenceModel,
        LdaMulticore,
        corpora,
        f1_score,
        gc,
        mo,
        nlp,
        np,
        pd,
        pipeline,
        pl,
        plt,
        precision_recall_curve,
        precision_score,
        pyLDAvis,
        re,
        recall_score,
        torch,
        tqdm,
        traceback,
    )


@app.cell
def _(pl):
    data = pl.read_csv("../data/data_final.csv", columns=["collection_name", "link_text", "link"]).unique(subset=["link_text"])
    noticias = data["link_text"].to_list()
    data
    return data, noticias


@app.cell
def _(mo):
    interrupt_button = mo.ui.run_button()
    interrupt_button
    return (interrupt_button,)


@app.cell
def _(corpora, interrupt_button, mo, nlp, noticias):
    mo.stop(not interrupt_button.value)
    docs_processados = []
    allowed_postags = ["NOUN", "ADJ", "VERB", "PROPN"]

    for texto in noticias:
        doc = nlp(texto.lower())
        tokens = [
            token.lemma_ for token in doc 
            if token.pos_ in allowed_postags 
            and not token.is_stop 
            and not token.is_punct
        ]
        docs_processados.append(tokens)

    stopwords_contexto = [
        'bolsonaro', 'haddad', 'lula', 'ciro', 'jair', 'fernando', 
        'candidato', 'presidencial', 'presidente', 'pt', 'psl', 
        'dizer', 'afirmar', 'falar', 'disse', 'brasil', 'brasileiro',
        'governo', 'ano', 'eleição', 'campanha', 'voto', 'Bolsonaro', 
        'Fernando', 'Paulo', 'the', 'is', 'in', 'guede', 'Lula', 
        'youtube', 'google', 'conteúdo', 'bbc', 'postr', 'Brasil', 'pais', 
        'dia', 'haver', 'of', 'to', 'Silva'
    ]

    docs_processados_limpos = []

    for tokens in docs_processados:
        tokens_limpos = [t for t in tokens if t not in stopwords_contexto]
        docs_processados_limpos.append(tokens_limpos)

    id2word = corpora.Dictionary(docs_processados_limpos)
    corpus = [id2word.doc2bow(text) for text in docs_processados_limpos]
    return corpus, docs_processados, id2word


@app.cell
def _(
    CoherenceModel,
    LdaMulticore,
    corpus,
    docs_processados,
    id2word,
    interrupt_button,
    mo,
    plt,
):
    mo.stop(not interrupt_button.value)
    def compute_coherence_values(dictionary, corpus, texts, limit, start=2, step=1):
        coherence_values = []
        model_list = []

        for num_topics in range(start, limit, step):
            model = LdaMulticore(
                corpus=corpus, 
                id2word=dictionary, 
                num_topics=num_topics, 
                random_state=100,
                passes=10,
                workers=2
            )
            model_list.append(model)

            coherencemodel = CoherenceModel(
                model=model, 
                texts=texts, 
                dictionary=dictionary, 
                coherence='c_v'
            )
            coherence_values.append(coherencemodel.get_coherence())

        return model_list, coherence_values

    start, limit, step = 4, 15, 1
    model_list, coherence_values = compute_coherence_values(
        dictionary=id2word, 
        corpus=corpus, 
        texts=docs_processados, 
        limit=limit, 
        start=start, 
        step=step
    )

    x = range(start, limit, step)
    plt.plot(x, coherence_values)
    plt.xlabel("Num Topics")
    plt.ylabel("Coherence score")
    plt.legend(("coherence_values"), loc='best')
    plt.show()

    for m, cv in zip(x, coherence_values):
        print(f"Num Topics = {m}  tem Coherence Score de {round(cv, 4)}")
    return (model_list,)


@app.cell
def _(corpus, id2word, interrupt_button, mo, model_list, pl, pyLDAvis, topic):
    mo.stop(not interrupt_button.value)
    best_model_index = 3
    best_lda_model = model_list[best_model_index]

    print(f"Mostrando tópicos para o modelo com {best_lda_model.num_topics} tópicos:\n")

    topics_data = []

    for idx, topicx in best_lda_model.print_topics(num_topics=-1, num_words=10):
        print(f"Tópico {idx}: {topic}")

        keywords = [t.split('*')[1].replace('"', '').strip() for t in topicx.split('+')]
        topics_data.append({'Topico_ID': idx, 'Palavras_Chave': ", ".join(keywords)})

    df_topics = pl.DataFrame(topics_data)
    vis = pyLDAvis.gensim_models.prepare(best_lda_model, corpus, id2word)
    return


@app.cell
def _(mo):
    interrupt_button_model = mo.ui.run_button()
    interrupt_button_model
    return (interrupt_button_model,)


@app.cell
def _(
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    gc,
    interrupt_button_model,
    mo,
    pd,
    pipeline,
    torch,
    tqdm,
    traceback,
):
    mo.stop(not interrupt_button_model.value)
    def load_translator():
        model_name = "unicamp-dl/translation-pt-en-t5"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        return tokenizer, model


    def translate_batch(texts, tokenizer, model, max_batch=8):
        device = next(model.parameters()).device
        outputs = []

        prefix = "translate Portuguese to English: "

        for i in range(0, len(texts), max_batch):
            batch_texts = [prefix + text for text in texts[i:i + max_batch]]

            encoded = tokenizer(
                batch_texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            ).to(device)

            gen = model.generate(
                **encoded,
                max_length=256,
            )

            decoded = tokenizer.batch_decode(gen, skip_special_tokens=True)
            outputs.extend(decoded)

        return outputs


    def run_hybrid_zero_shot_pipeline(texts, topics, models_config, batch_size=8):
        dfs = {}
        device = 0 if torch.cuda.is_available() else -1

        nmt_tokenizer = None
        nmt_model = None

        for config in tqdm(models_config, desc="Processando modelos"):
            model_name = config["name"]
            model_lang = config.get("lang", "pt")

            print(f"\n{'=' * 60}")
            print(f"Modelo: {model_name} | Modo: {model_lang.upper()}")
            print(f"{'=' * 60}")

            try:
                current_topics = topics
                topic_map = None
                hypothesis_template = "Este texto trata de {}."

                if model_lang == "en":
                    if nmt_model is None:
                        print("Carregando modelo de tradução (Unicamp T5)...")
                        nmt_tokenizer, nmt_model = load_translator()

                    print("Traduzindo tópicos para inglês...")
                    translated_topics = translate_batch(
                        topics,
                        nmt_tokenizer,
                        nmt_model,
                        max_batch=batch_size
                    )

                    topic_map = dict(zip(translated_topics, topics))
                    current_topics = translated_topics
                    hypothesis_template = "This text is about {}."

                tokenizer_kwargs = {
                    "truncation": True,
                    "padding": True,
                    "max_length": 512,
                    "return_tensors": "pt",
                }

                classifier = pipeline(
                    "zero-shot-classification",
                    model=model_name,
                    device=device,
                    tokenizer_kwargs=tokenizer_kwargs,
                    framework="pt"
                )

                outputs = []

                with tqdm(total=len(texts), desc="Classificando", unit="txt") as pbar:
                    for i in range(0, len(texts), batch_size):
                        batch_texts = texts[i:i + batch_size]
                        original_batch_texts = batch_texts.copy()

                        if model_lang == "en":
                            try:
                                batch_texts = translate_batch(
                                    batch_texts,
                                    nmt_tokenizer,
                                    nmt_model,
                                    max_batch=batch_size
                                )
                            except Exception as e:
                                print(f"Erro na tradução do batch: {e}")
                                batch_texts = original_batch_texts

                        try:
                            batch_outputs = classifier(
                                batch_texts,
                                candidate_labels=current_topics,
                                multi_label=True,
                                hypothesis_template=hypothesis_template,
                            )

                            if not isinstance(batch_outputs, list):
                                batch_outputs = [batch_outputs]

                            for idx, out in enumerate(batch_outputs):
                                out["sequence"] = original_batch_texts[idx]

                            outputs.extend(batch_outputs)

                        except Exception as batch_error:
                            print(f"\nErro no batch {i // batch_size}: {batch_error}")
                            for original_text in original_batch_texts:
                                outputs.append({
                                    "sequence": original_text,
                                    "labels": [],
                                    "scores": []
                                })

                        pbar.update(len(original_batch_texts))

                data_rows = []
                for output in outputs:
                    row = {"texto_original": output.get("sequence", "")}
                    labels = output.get("labels", [])
                    scores = output.get("scores", [])

                    for label, score in zip(labels, scores):
                        final_label = topic_map[label] if topic_map else label
                        row[final_label] = score

                    for topic in topics:
                        if topic not in row:
                            row[topic] = 0.0

                    data_rows.append(row)

                df_model = pd.DataFrame(data_rows)
                base_cols = ["texto_original"]
                existing_topics = [t for t in topics if t in df_model.columns]
                df_model = df_model[base_cols + existing_topics]

                dfs[model_name] = df_model

                del classifier
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                gc.collect()

                print(f"✓ Modelo {model_name} finalizado.")

            except Exception as e:
                print(f"✗ Erro crítico em {model_name}: {e}")
                traceback.print_exc()
                continue

        return dfs
    return (run_hybrid_zero_shot_pipeline,)


@app.cell
def _(interrupt_button_model, mo, noticias, re, run_hybrid_zero_shot_pipeline):
    mo.stop(not interrupt_button_model.value)
    topicos_definidos = [
        "economia",
        "educação",
        "saúde",
        "segurança",
        "cultura",
        "religião",
        "desinformação",
        "desarmamento",
        "eleição",
        "política",
        "corrupção"
    ]

    modelos_config = [
        {
            "name": "facebook/bart-large-mnli",
            "lang": "en"
        },
        {
            "name": "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
            "lang": "pt"
        },
        {
            "name": "MoritzLaurer/bge-m3-zeroshot-v2.0",
            "lang": "pt"
        }
    ]

    resultados = run_hybrid_zero_shot_pipeline(
        noticias,
        topicos_definidos,
        modelos_config,
        batch_size=4
    )

    for model_name, df in resultados.items():
        safe_name = re.sub(r"[^\w\-_\.]", "_", model_name)
        output_path = f"resultado_zero_shot_{safe_name}.csv"
        df.to_csv(output_path, index=False, encoding="utf-8-sig")

        print(f"\n📊 Modelo: {model_name}")
        print(f"📁 Salvo: {output_path}")

        topic_columns = [col for col in df.columns if col != "texto_original"]
        if topic_columns:
            print("Médias de scores:")
            for topic in topic_columns:
                mean = df[topic].mean()
                print(f"  {topic}: {mean:.3f}")

        print("-" * 60)
    return (topic,)


@app.cell
def _(data, pl):
    mdebert = pl.read_csv("../data/zero_shot_results/resultado_zero_shot_MoritzLaurer_mDeBERTa-v3-base-xnli-multilingual-nli-2mil7.csv").drop("text", "clean_text", "topic", "vacina", "meio ambiente", "desarmamento")

    bge = pl.read_csv("../data/zero_shot_results/resultado_zero_shot_MoritzLaurer_bge-m3-zeroshot-v2.0.csv").rename({"política": "politica"}).join(data.select("link_text", "collection_name"), left_on="texto_original", right_on="link_text").drop("texto_original", "desarmamento")

    facebook_english = pl.read_csv("../data/zero_shot_results/resultado_zero_shot_facebook_bart-large-mnli_english.csv").rename({"política": "politica"}).join(data.select("link_text", "collection_name"), left_on="texto_original", right_on="link_text").drop("texto_original", "desarmamento")

    true = pl.read_csv("../data/zero_shot_results/avaliacao_topicos_thiago.csv").join(data.select("link", "collection_name"), on="link").drop("link", "desarmamento")
    return bge, facebook_english, mdebert, true


@app.cell
def _(
    bge,
    f1_score,
    facebook_english,
    mdebert,
    np,
    precision_recall_curve,
    precision_score,
    recall_score,
    true,
):
    dfs = {
        "mdebert": mdebert,
        "bge": bge,
        "facebook_english": facebook_english,
    }

    df_true = true.to_pandas()

    topicos = [
        "economia", "educação", "saúde", "segurança", 
        "cultura", "religião", "desinformação",
        "eleição", "politica", "corrupção"
    ]

    epsilon = 1e-6

    results = {}

    for model_name_val, df_model in dfs.items():

        df_validation = df_model.join(true, on="collection_name").to_pandas()

        results[model_name_val] = {
            "thresholds": {},
            "metrics": {},
            "weighted_f1_avg": 0.0
        }

        f1_accumulator = 0.0
        total_support = 0

        for t in topicos:
            try:
                y_true = df_validation[f"{t}_right"]
            except:
                y_true = df_validation[f"política_right"]

            y_pred_probs = df_validation[t]

            prec, rec, thresh = precision_recall_curve(y_true, y_pred_probs)
            f1 = 2 * prec * rec / (prec + rec + epsilon)

            best_idx = np.argmax(f1)
            best_threshold = thresh[best_idx]

            results[model_name_val]["thresholds"][t] = best_threshold

            y_pred = (y_pred_probs >= best_threshold).astype(int)

            precision2 = precision_score(y_true, y_pred, zero_division=0)
            recall2 = recall_score(y_true, y_pred, zero_division=0)
            f12 = f1_score(y_true, y_pred, zero_division=0)

            results[model_name_val]["metrics"][t] = {
                "precision": precision2,
                "recall": recall2,
                "f1": f12,
                "support": y_true.sum()
            }

            support = y_true.sum()
            f1_accumulator += f12 * support
            total_support += support

        if total_support > 0:
            results[model_name_val]["weighted_f1_avg"] = f1_accumulator / total_support
        else:
            results[model_name_val]["weighted_f1_avg"] = 0.0

    results
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
