import gradio as gr
import json
import os
import tempfile

LANG_DIR = "./human_eval"
SAVE_DIR = "./annotations"
os.makedirs(SAVE_DIR, exist_ok=True)

data = []
user_annotations = []
current_lang = ""

language_options = sorted([f for f in os.listdir(LANG_DIR)])


def load_data_for_lang(lang_pair):
    global data, user_annotations, current_lang
    file_path = os.path.join(LANG_DIR, lang_pair, f"{lang_pair}.json")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    user_annotations = []
    current_lang = lang_pair
    return (
        0,
        data[0]["source"],
        data[0]["hypothesis"],
        f"0/{len(data)} loaded from {lang_pair}",
    )


def restore_previous_annotations(file_obj):
    global data, user_annotations, current_lang

    with open(file_obj.name, "r", encoding="utf-8") as f:
        user_annotations = json.load(f)

    if not user_annotations:
        return 0, "", "", "No annotations found."

    restored_lang = user_annotations[0].get("lang_pair", None)
    if not restored_lang or not os.path.exists(
        os.path.join(LANG_DIR, restored_lang, f"{restored_lang}.json")
    ):
        return 0, "", "", "❌ Language pair info missing or file not found."

    file_path = os.path.join(LANG_DIR, restored_lang, f"{restored_lang}.json")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    current_lang = restored_lang

    # Back to last index
    last_index = user_annotations[-1]["index"] + 1
    if last_index >= len(data):
        return (
            last_index,
            "",
            "",
            f"✅ Already completed {len(data)} samples of {restored_lang}.",
        )

    return (
        last_index,
        data[last_index]["source"],
        data[last_index]["hypothesis"],
        f"Restored {restored_lang}: {last_index}/{len(data)}",
        restored_lang,
    )


def load_sample(i):
    if not data:
        return "", ""
    entry = data[int(i)]
    return entry["source"], entry["hypothesis"]


def annotate(index, score, comment, annotator):
    global current_lang
    index = int(index)
    entry = data[index]
    record = {
        "index": index,
        "annotator": annotator,
        "lang_pair": current_lang,
        "source": entry["source"],
        "hypothesis": entry["hypothesis"],
        "score": score,
        "comment": comment,
    }
    user_annotations.append(record)

    # 保存到服务器端（可选）
    # save_path = os.path.join(SAVE_DIR, f"annotations_{annotator}.jsonl")
    # with open(save_path, "a", encoding="utf-8") as f:
    #     f.write(json.dumps(record, ensure_ascii=False) + "\n")

    completed = index + 1
    if completed >= len(data):
        return (
            "🎉 All samples annotated!",
            index,
            f"✅ Completed {completed}/{len(data)} samples.",
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(visible=True),
        )

    next_index = index + 1
    progress = f"{completed}/{len(data)} annotated by {annotator}"
    return (
        "✅ Saved",
        next_index,
        progress,
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(visible=False),
    )


def export_results():
    if not user_annotations:
        raise ValueError("No annotations to export.")
    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=".json", mode="w", encoding="utf-8"
    )
    json.dump(user_annotations, tmp, ensure_ascii=False, indent=2)
    tmp.close()
    return tmp.name, gr.update(visible=True, value=tmp.name)


# ======== UI ========
with gr.Blocks() as demo:
    gr.Markdown("## 📝 Direct Assessment Annotation Tool")

    with gr.Row():
        lang_choice = gr.Dropdown(
            label="Choose Language Pair",
            choices=language_options,
            value=language_options[0],
        )
        load_button = gr.Button("🔄 Load Data")

    with gr.Row():
        upload_file = gr.File(
            label="📤 Upload Previous Annotations", file_types=[".json"]
        )
        export_button = gr.Button("📥 Export My Results")

    with gr.Row():
        annotator = gr.Textbox(
            label="Annotator ID",
            placeholder="Enter your name or ID",
            value="annotator_1",
        )
        progress = gr.Textbox(label="Progress", interactive=False)

    idx = gr.Number(value=0, visible=False)
    source = gr.Textbox(label="Source Sentence", interactive=False)
    hyp = gr.Textbox(label="Machine Translation", interactive=False)
    score = gr.Slider(0, 100, step=1, label="Translation Quality Score")
    comment = gr.Textbox(lines=2, placeholder="Optional comment...", label="Comment")
    output = gr.Textbox(label="Status", interactive=False)
    next_button = gr.Button("Submit and Next")
    export_file = gr.File(label="Download your results", visible=False)

    load_button.click(
        fn=load_data_for_lang,
        inputs=[lang_choice],
        outputs=[idx, source, hyp, progress],
    )
    upload_file.change(
        fn=restore_previous_annotations,
        inputs=[upload_file],
        outputs=[idx, source, hyp, progress, lang_choice],
    )
    next_button.click(
        fn=annotate,
        inputs=[idx, score, comment, annotator],
        outputs=[
            output,
            idx,
            progress,
            score,
            comment,
            next_button,
            annotator,
            export_file,
        ],
    )
    export_button.click(
        fn=export_results,
        inputs=[],
        outputs=[
            export_file,
            export_file,
        ],  # 绑定两次 export_file，第二个用于更新它的可见性和路径
    )
    idx.change(fn=load_sample, inputs=idx, outputs=[source, hyp])
    demo.load(fn=load_sample, inputs=[idx], outputs=[source, hyp])

demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
