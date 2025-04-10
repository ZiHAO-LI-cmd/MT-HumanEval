import gradio as gr
import json
import os
import tempfile

DATA_FILE = "./test_data.json"

# 本地或 Render 环境下的保存目录
SAVE_DIR = "./annotations"
os.makedirs(SAVE_DIR, exist_ok=True)

# 读取样本数据
with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# 用于记录当前用户的所有打分（浏览器内存）
user_annotations = []

# 保存标注记录
def annotate(index, score, comment, annotator):
    entry = data[index]
    record = {
        "index": index,
        "annotator": annotator,
        "source": entry["source"],
        "hypothesis": entry["hypothesis"],
        "score": score,
        "comment": comment,
    }

    # 1. 保存到用户 session 记录
    user_annotations.append(record)

    # 2. 仍然保存到服务器端（可选）
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
            gr.update(visible=True)  # 显示导出按钮
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
        gr.update(visible=False)
    )

# 加载样本
def load_sample(i):
    entry = data[i]
    return entry["source"], entry["hypothesis"]

# 导出打分结果为 JSON 文件
def export_results():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8")
    json.dump(user_annotations, tmp, ensure_ascii=False, indent=2)
    tmp.close()
    return tmp.name

with gr.Blocks() as demo:
    gr.Markdown("## Direct Assessment Annotation")

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

    # 新增：导出按钮和文件下载组件
    export_button = gr.Button("📥 Export My Results")
    export_file = gr.File(label="Download your results", visible=False)

    # 原打分按钮逻辑
    next_button.click(
        fn=annotate,
        inputs=[idx, score, comment, annotator],
        outputs=[output, idx, progress, score, comment, next_button, annotator, export_file],
    )

    # 新增导出逻辑
    export_button.click(fn=export_results, outputs=export_file)

    idx.change(fn=load_sample, inputs=idx, outputs=[source, hyp])
    demo.load(fn=load_sample, inputs=[idx], outputs=[source, hyp])

demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))