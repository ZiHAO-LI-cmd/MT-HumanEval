import gradio as gr
import json
import os
import tempfile

# ======== 设置路径 ========
LANG_DIR = "./human_eval"  # 含有语言对子文件夹的目录
SAVE_DIR = "./annotations"  # 保存标注记录的目录
os.makedirs(SAVE_DIR, exist_ok=True)

# ======== 初始化数据结构 ========
data = []
user_annotations = []

# ======== 获取可用语言对列表 ========
language_options = sorted([f for f in os.listdir(LANG_DIR)])


# ======== 加载选择的语言对数据 ========
def load_data_for_lang(lang_pair):
    global data, user_annotations
    file_path = os.path.join(LANG_DIR, lang_pair, f"{lang_pair}.json")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    user_annotations = []
    return (
        0,
        data[0]["source"],
        data[0]["hypothesis"],
        f"0/{len(data)} loaded from {lang_pair}",
    )


# ======== 读取当前样本 ========
def load_sample(i):
    if not data:
        return "", ""
    entry = data[int(i)]
    return entry["source"], entry["hypothesis"]


# ======== 提交打分并进入下一条 ========
def annotate(index, score, comment, annotator):
    index = int(index)
    entry = data[index]
    record = {
        "index": index,
        "annotator": annotator,
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


# ======== 导出打分结果 ========
def export_results():
    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=".json", mode="w", encoding="utf-8"
    )
    json.dump(user_annotations, tmp, ensure_ascii=False, indent=2)
    tmp.close()
    return tmp.name


# ======== UI 构建 ========
with gr.Blocks() as demo:
    gr.Markdown("## Direct Assessment Annotation Tool")

    with gr.Row():
        lang_choice = gr.Dropdown(
            label="Choose Language Pair",
            choices=language_options,
            value=language_options[0],
        )
        load_button = gr.Button("🔄 Load Data")

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

    export_button = gr.Button("📥 Export My Results")
    export_file = gr.File(label="Download your results", visible=False)

    # 行为绑定
    load_button.click(
        fn=load_data_for_lang,
        inputs=[lang_choice],
        outputs=[idx, source, hyp, progress],
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
    export_button.click(fn=export_results, outputs=export_file)
    idx.change(fn=load_sample, inputs=idx, outputs=[source, hyp])
    demo.load(fn=load_sample, inputs=[idx], outputs=[source, hyp])

# ======== 启动应用 ========
demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
