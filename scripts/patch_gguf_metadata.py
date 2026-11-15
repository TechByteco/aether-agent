"""
Patch GGUF Adapter Metadata and Tensor Names for Ollama llama.cpp
"""
import os
import sys
import gguf

def patch_gguf_adapter(input_path: str, output_path: str):
    print(f"Reading GGUF: {input_path}")
    reader = gguf.GGUFReader(input_path)
    print(f"Loaded {len(reader.tensors)} tensors, {len(reader.fields)} fields.")

    writer = gguf.GGUFWriter(output_path, "llama")
    
    # 1. Write KV metadata
    writer.add_string("general.architecture", "llama")
    writer.add_string("general.type", "adapter")
    writer.add_string("adapter.type", "lora")
    writer.add_string("general.name", "Aether_Lora_Adapter")
    writer.add_float32("adapter.lora.alpha", 16.0)

    # 2. Add all tensors with lowercase .lora_a and .lora_b
    for tensor in reader.tensors:
        name = tensor.name
        # Convert .loraA / .loraB to .lora_a / .lora_b
        if name.endswith(".loraA"):
            name = name[:-6] + ".lora_a"
        elif name.endswith(".loraB"):
            name = name[:-6] + ".lora_b"
        elif ".loraA." in name:
            name = name.replace(".loraA.", ".lora_a.")
        elif ".loraB." in name:
            name = name.replace(".loraB.", ".lora_b.")
        elif name.endswith(".lora_A"):
            name = name[:-7] + ".lora_a"
        elif name.endswith(".lora_B"):
            name = name[:-7] + ".lora_b"

        writer.add_tensor(name, tensor.data)

    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file()
    writer.close()
    print(f"Successfully saved patched adapter to: {output_path}")

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "C:/Users/saali/Downloads/aether_adapter (1).gguf"
    dst = sys.argv[2] if len(sys.argv) > 2 else "data/models/aether_adapter.gguf"
    patch_gguf_adapter(src, dst)
