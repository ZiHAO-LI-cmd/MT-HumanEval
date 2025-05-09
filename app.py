import gradio as gr
import json
import os
import tempfile

LANG_DIR = "./human_eval"
SAVE_DIR = "./annotations"
os.makedirs(SAVE_DIR, exist_ok=True)

# 全局变量 data, user_annotations, current_lang 已被移除

language_options = sorted([f for f in os.listdir(LANG_DIR)])

# --- 函数修改 ---
# 每个需要访问或修改 data, user_annotations, current_lang 的函数
# 都需要将 app_state 作为输入，并通常作为输出

def load_data_for_lang(lang_pair, current_app_state): # 接收 app_state
    file_path = os.path.join(LANG_DIR, lang_pair, f"{lang_pair}.json")
    with open(file_path, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)

    new_app_state = { # 创建新的状态
        "data": loaded_data,
        "user_annotations": [], # Reset annotations for new language
        "current_lang": lang_pair
    }
    if not loaded_data:
        return 0, "", "", f"0/0 loaded from {lang_pair}", new_app_state

    return (
        0,
        loaded_data[0]["source"],
        loaded_data[0]["hypothesis"],
        f"0/{len(loaded_data)} loaded from {lang_pair}",
        new_app_state, # 返回更新后的状态
    )

def restore_previous_annotations(file_obj, current_app_state): # 接收 app_state
    if file_obj is None: # Check if a file was actually uploaded
        return 0, "", "", "No file uploaded.", current_app_state, language_options[0] if language_options else ""


    with open(file_obj.name, "r", encoding="utf-8") as f:
        uploaded_annotations = json.load(f)

    if not uploaded_annotations:
        return 0, "", "", "No annotations found in file.", current_app_state, language_options[0] if language_options else ""


    restored_lang = uploaded_annotations[0].get("lang_pair", None)
    if not restored_lang or not os.path.exists(
        os.path.join(LANG_DIR, restored_lang, f"{restored_lang}.json")
    ):
        return 0, "", "", "❌ Language pair info missing or file not found.", current_app_state, language_options[0] if language_options else ""


    file_path = os.path.join(LANG_DIR, restored_lang, f"{restored_lang}.json")
    with open(file_path, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)

    new_app_state = { # 创建新的状态
        "data": loaded_data,
        "user_annotations": uploaded_annotations,
        "current_lang": restored_lang
    }

    last_index = 0
    if new_app_state["user_annotations"]: # Check if there are any annotations
        last_index = new_app_state["user_annotations"][-1].get("index", -1) + 1


    if last_index >= len(new_app_state["data"]):
        return (
            last_index,
            "",
            "",
            f"✅ Already completed {len(new_app_state['data'])} samples of {restored_lang}.",
            new_app_state, # 返回状态
            restored_lang,
        )

    return (
        last_index,
        new_app_state["data"][last_index]["source"],
        new_app_state["data"][last_index]["hypothesis"],
        f"Restored {restored_lang}: {last_index}/{len(new_app_state['data'])}",
        new_app_state, # 返回状态
        restored_lang, # To update the dropdown
    )


def load_sample(i, current_app_state): # 接收 app_state
    # 这个函数只读取状态，不修改，所以不需要返回 app_state
    # 但仍然需要接收它来获取数据
    data_from_state = current_app_state["data"]
    if not data_from_state or int(i) >= len(data_from_state) or int(i) < 0 :
        return "", ""
    entry = data_from_state[int(i)]
    return entry["source"], entry["hypothesis"]

def annotate(index, score, comment, annotator, current_app_state): # 接收 app_state
    index = int(index)
    app_data = current_app_state["data"]
    app_current_lang = current_app_state["current_lang"]
    app_user_annotations = list(current_app_state["user_annotations"]) # Create a mutable copy

    if index >= len(app_data): # Safety check
        return (
            "Error: Index out of bounds.",
            index,
            f"Error annotating.",
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(visible=False),
            current_app_state # Return original state
        )

    entry = app_data[index]
    record = {
        "index": index,
        "annotator": annotator,
        "lang_pair": app_current_lang,
        "source": entry["source"],
        "hypothesis": entry["hypothesis"],
        "score": score,
        "comment": comment,
    }

    # Update user_annotations in the copied list
    app_user_annotations = [
        rec
        for rec in app_user_annotations
        if not (rec["index"] == index and rec["annotator"] == annotator) # More robust removal
    ]
    app_user_annotations.append(record)
    app_user_annotations.sort(key=lambda x: x["index"]) # Keep sorted if needed

    # 更新状态
    new_app_state = {
        "data": app_data,
        "user_annotations": app_user_annotations,
        "current_lang": app_current_lang
    }

    completed = index + 1
    if completed >= len(app_data):
        return (
            "🎉 All samples annotated!",
            index, # or completed
            f"✅ Completed {completed}/{len(app_data)} samples.",
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(visible=True),
            new_app_state, # 返回状态
        )

    next_index = index + 1
    next_entry = app_data[next_index]

    prev_score, prev_comment = 0, ""
    for rec in new_app_state["user_annotations"]:
        if rec["index"] == next_index and rec["annotator"] == annotator:
            prev_score = rec["score"]
            prev_comment = rec["comment"]
            break

    progress_text = f"{completed}/{len(app_data)} annotated by {annotator}"
    is_at_start = next_index == 0
    return (
        "✅ Saved",
        next_index,
        progress_text,
        gr.update(value=prev_score, interactive=True),
        gr.update(value=prev_comment, interactive=True),
        gr.update(interactive=not is_at_start),
        gr.update(interactive=True),
        gr.update(visible=False),
        new_app_state, # 返回状态
    )


def go_previous(index, annotator, current_app_state): # 接收 app_state
    index = int(index)
    app_data = current_app_state["data"]
    app_user_annotations = current_app_state["user_annotations"]

    if not app_data: # No data loaded
        return 0, "", "", 0, "", "No data loaded.", gr.update(interactive=False), gr.update(interactive=False)


    if index <= 0:
        prev_index = 0
        is_at_start = True
    else:
        prev_index = index - 1
        is_at_start = prev_index == 0

    entry = app_data[prev_index]
    prev_score, prev_comment = 0, ""
    for rec in app_user_annotations:
        if rec["index"] == prev_index and rec["annotator"] == annotator:
            prev_score = rec["score"]
            prev_comment = rec["comment"]
            break

    progress_text = f"{prev_index}/{len(app_data)} annotated by {annotator}"
    if not app_data:
        progress_text = "No data loaded."


    # This function doesn't change the state, so no need to return current_app_state unless it was modified
    # However, to be consistent with other functions that MIGHT modify state or if you plan to,
    # it's good practice to include it. In this specific case, it's only reading.
    return (
        prev_index,
        entry["source"],
        entry["hypothesis"],
        prev_score,
        prev_comment,
        progress_text,
        gr.update(interactive=not is_at_start),
        gr.update(interactive=True),
        # No app_state in outputs here if it's not being changed
    )


def export_results(current_app_state): # 接收 app_state
    app_user_annotations = current_app_state["user_annotations"]
    if not app_user_annotations:
        # raise ValueError("No annotations to export.") # This will crash the app
        # Instead, show a message or disable the button if no annotations
        gr.Warning("No annotations to export.")
        return None, gr.update(visible=False)

    # Create a temporary file for download
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".json", mode="w", encoding="utf-8"
    ) as tmp:
        json.dump(app_user_annotations, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name # Get the path before closing

    # The file is closed when exiting the 'with' block
    return tmp_path, gr.update(visible=True, value=tmp_path)


# ======== UI ========

with gr.Blocks() as demo:
    # Define session state
    app_state = gr.State(
        value={"data": [], "user_annotations": [], "current_lang": ""}
    )

    gr.Markdown("## 📝 Direct Assessment Annotation Tool")
    with gr.Row():
        lang_choice = gr.Dropdown(
            label="Choose Language Pair",
            choices=language_options,
            value=language_options[0] if language_options else None, # Handle empty options
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

    idx = gr.Number(value=0, visible=False, label="Current Index") # Added label for clarity if made visible
    source = gr.Textbox(label="Source Sentence", interactive=False, lines=3)
    hyp = gr.Textbox(label="Machine Translation", interactive=False, lines=3)
    score = gr.Slider(0, 100, step=1, label="Translation Quality Score", value=0)
    comment = gr.Textbox(lines=2, placeholder="Optional comment...", label="Comment")
    output = gr.Textbox(label="Status", interactive=False)
    previous_button = gr.Button("⏪Previous", interactive=False) # Initially disabled
    next_button = gr.Button("⏩Next", interactive=False) # Initially disabled
    export_file = gr.File(label="Download your results", visible=False, interactive=False)

    # --- Component Event Handlers ---
    # Add app_state to inputs and outputs where necessary

    load_button.click(
        fn=load_data_for_lang,
        inputs=[lang_choice, app_state], # Add app_state
        outputs=[idx, source, hyp, progress, app_state], # Add app_state
    ).then(
        lambda: (gr.update(interactive=True), gr.update(interactive=False)), # Enable Next, Disable Prev
        outputs=[next_button, previous_button]
    )


    upload_file.change(
        fn=restore_previous_annotations,
        inputs=[upload_file, app_state], # Add app_state
        outputs=[idx, source, hyp, progress, app_state, lang_choice], # Add app_state and lang_choice to update dropdown
    ).then(
        lambda x: (gr.update(interactive=True), gr.update(interactive=x!=0)), # Enable Next, Prev based on index
        inputs=[idx],
        outputs=[next_button, previous_button]
    )

    next_button.click(
        fn=annotate,
        inputs=[idx, score, comment, annotator, app_state], # Add app_state
        outputs=[
            output,
            idx,
            progress,
            score, # To reset/update score for next item
            comment, # To reset/update comment for next item
            previous_button,
            next_button,
            export_file, # This is the download component
            app_state, # Add app_state
        ],
    )

    previous_button.click(
        fn=go_previous,
        inputs=[idx, annotator, app_state], # Add app_state
        outputs=[
            idx,
            source,
            hyp,
            score,
            comment,
            progress,
            previous_button,
            next_button,
            # No app_state output if go_previous doesn't modify it
        ],
    )

    export_button.click(
        fn=export_results,
        inputs=[app_state], # Add app_state
        outputs=[
            export_file, # For the file content/path
            export_file, # For updating visibility/value
        ],
    )

    # This loads the sample when the index changes, e.g., after load_data or annotate
    idx.change(fn=load_sample, inputs=[idx, app_state], outputs=[source, hyp])

    # Initial load logic (optional, if you want something on app start)
    # Consider what should happen if language_options is empty
    def initial_load_or_message(current_app_state):
        if language_options:
            # This duplicates load_data_for_lang slightly, could be refactored
            lang_pair_to_load = language_options[0]
            idx_val, src_val, hyp_val, prog_val, new_app_state = load_data_for_lang(lang_pair_to_load, current_app_state)
            return idx_val, src_val, hyp_val, prog_val, new_app_state, lang_pair_to_load, gr.update(interactive=True), gr.update(interactive=False)
        else:
            return 0, "No languages found in LANG_DIR.", "", "Please add language files.", current_app_state, None, gr.update(interactive=False), gr.update(interactive=False)

    # demo.load is tricky with state management if the function also needs to return the state.
    # It's often better to trigger an initial load via a button or specific logic after UI setup.
    # If you must use demo.load and it needs to initialize state, ensure it correctly returns the state.
    # For simplicity, let's ensure load_button handles enabling next/prev:
    # demo.load(
    #    fn=initial_load_or_message,
    #    inputs=[app_state],
    #    outputs=[idx, source, hyp, progress, app_state, lang_choice, next_button, previous_button]
    # )
    # A simpler demo.load without initial data loading:
    demo.load(lambda: (gr.update(interactive=False), gr.update(interactive=False)), outputs=[next_button, previous_button])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))