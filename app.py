import gradio as gr
import json
import os

# ==== 路径设置 ====
DATA_FILE = "./test_data.json"

# Railway 上的挂载磁盘路径，或回退为本地路径
SAVE_DIR = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "./annotations")
os.makedirs(SAVE_DIR, exist_ok=True)
# ==================

# 读取样本数据
with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)


# 保存标注并控制状态
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

    save_path = os.path.join(SAVE_DIR, f"annotations_{annotator}.jsonl")
    with open(save_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

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
    )


def load_sample(i):
    entry = data[i]
    return entry["source"], entry["hypothesis"]


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

    next_button.click(
        fn=annotate,
        inputs=[idx, score, comment, annotator],
        outputs=[output, idx, progress, score, comment, next_button, annotator],
    )
    idx.change(fn=load_sample, inputs=idx, outputs=[source, hyp])
    demo.load(fn=load_sample, inputs=[idx], outputs=[source, hyp])

# 🚀 监听 Railway 提供的端口（默认 7860）
demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
