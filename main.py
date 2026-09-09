import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

# Cap BLAS/ONNX worker threads to prevent full CPU pegging / system stutter
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")
os.environ.setdefault("MKL_NUM_THREADS", "4")

# Ensure workspace root is always in Python search path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import gradio as gr

from universal_parser import parse, to_chunks, to_graph, to_markdown

# Hugging Face ZeroGPU compatibility handler (startup check only)
try:
    import spaces

    @spaces.GPU(duration=1)
    def _zero_gpu_startup_guard():
        """Satisfies ZeroGPU startup check without consuming user GPU quota."""
        return None

except (ImportError, Exception):
    pass


def process_document(file_obj, max_chunk_tokens, progress=gr.Progress(track_tqdm=True)):
    if file_obj is None:
        return (
            "### Please upload a document to begin parsing.",
            "[]",
            "{}",
            "{}",
            "Zero input provided.",
        )

    file_path = file_obj.name
    start_time = time.perf_counter()

    try:
        progress(0.1, desc="Reading file & extracting document structure...")
        doc = parse(file_path)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 1. Render Markdown
        progress(0.6, desc="Rendering Markdown & RAG chunks...")
        markdown_output = to_markdown(doc)

        # 2. Render Hierarchical RAG Chunks (capped in UI preview to prevent browser lag)
        chunks = to_chunks(doc, max_tokens=int(max_chunk_tokens))
        chunk_data = [
            {
                "chunk_id": c.chunk_id,
                "headings": c.headings,
                "estimated_tokens": c.estimated_tokens,
                "page_numbers": c.page_numbers,
                "text": c.text,
            }
            for c in chunks
        ]
        display_chunks = chunk_data[:100]
        if len(chunk_data) > 100:
            display_chunks.append(
                {"_ui_note": f"Showing first 100 of {len(chunk_data)} total chunks for UI speed."}
            )
        chunks_json = json.dumps(display_chunks, indent=2)

        # 3. Render Knowledge Graph
        progress(0.8, desc="Building Knowledge Graph & Schemas...")
        graph = to_graph(doc)
        graph_dict = asdict(graph)
        if len(graph_dict.get("nodes", [])) > 200:
            total_nodes = len(graph_dict["nodes"])
            graph_dict["nodes"] = graph_dict["nodes"][:200]
            graph_dict["_ui_note"] = f"Displaying first 200 of {total_nodes} nodes in UI."
        graph_json = json.dumps(graph_dict, indent=2)

        # 4. Render Raw Schema JSON (capped in browser code viewer for smoothness)
        doc_dump = doc.model_dump()
        if len(doc_dump.get("content_tree", [])) > 200:
            total_elements = len(doc_dump["content_tree"])
            doc_dump["content_tree"] = doc_dump["content_tree"][:200]
            doc_dump["_ui_note"] = (
                f"Displaying first 200 of {total_elements} elements in UI. Document is 100% parsed."
            )
        schema_json = json.dumps(doc_dump, indent=2, default=str)

        # 5. Telemetry & Metrics Summary
        element_types = {}
        for elem in doc.content_tree:
            element_types[elem.type] = element_types.get(elem.type, 0) + 1

        metrics_summary = f"""### Extraction Telemetry
- **File Name:** `{doc.metadata.file_name}`
- **Format:** `{doc.metadata.file_type.upper()}`
- **Parsing Latency:** `{elapsed_ms} ms`
- **Total Pages:** `{doc.metadata.page_count}`
- **Total Elements:** `{len(doc.content_tree)}`
- **Generated Chunks:** `{len(chunks)}`

#### Element Distribution
""" + "\n".join([f"- **{k.capitalize()}:** `{v}`" for k, v in element_types.items()])

        progress(1.0, desc="Complete!")
        return (
            markdown_output,
            chunks_json,
            graph_json,
            schema_json,
            metrics_summary,
        )

    except Exception as e:
        error_msg = f"### Extraction Error\nAn error occurred while processing the file: `{str(e)}`"
        return error_msg, "[]", "{}", "{}", "Processing failed."


# Build Gradio UI
with gr.Blocks(
    title="Universal Document Parser — Zero-GPU RAG Ingestion",
    theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
) as demo:
    gr.Markdown(
        """
        # Universal Document Parser
        ### Zero-GPU, CPU-Only Production Ingestion Engine for RAG Pipelines & AI Agents

        Upload any document below (PDF, DOCX, XLSX, PPTX, HTML, EPUB, CSV, Parquet, JSON, XML, EML, MSG, Image) to extract structured Markdown, hierarchical RAG chunks, knowledge graph entities, and schema telemetry in real-time.
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(
                label="Upload Document",
                file_types=[
                    ".pdf",
                    ".docx",
                    ".xlsx",
                    ".pptx",
                    ".html",
                    ".epub",
                    ".csv",
                    ".tsv",
                    ".parquet",
                    ".json",
                    ".xml",
                    ".eml",
                    ".msg",
                    ".mbox",
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".webp",
                ],
            )
            chunk_token_slider = gr.Slider(
                minimum=128,
                maximum=2048,
                value=512,
                step=64,
                label="RAG Chunk Max Tokens",
                info="Token budget per chunk for hierarchical breadcrumbs.",
            )
            parse_btn = gr.Button("Parse Document", variant="primary", size="lg")
            metrics_output = gr.Markdown(label="Extraction Telemetry")

        with gr.Column(scale=2):
            with gr.Tabs():
                with gr.TabItem("Markdown Output"):
                    markdown_output = gr.Markdown(label="Extracted Markdown")
                with gr.TabItem("RAG Chunks"):
                    chunks_output = gr.Code(label="Hierarchical Chunks JSON", language="json")
                with gr.TabItem("Knowledge Graph"):
                    graph_output = gr.Code(label="Graph Nodes & Edges JSON", language="json")
                with gr.TabItem("Full Pydantic Schema"):
                    schema_output = gr.Code(label="Document Schema JSON", language="json")

    parse_btn.click(
        fn=process_document,
        inputs=[file_input, chunk_token_slider],
        outputs=[
            markdown_output,
            chunks_output,
            graph_output,
            schema_output,
            metrics_output,
        ],
        api_name=False,
    )

if __name__ == "__main__":
    demo.launch(ssr_mode=False)
