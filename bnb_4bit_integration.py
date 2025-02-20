# -*- coding: utf-8 -*-
"""bnb-4bit-integration.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ge2F1QSK8Q7h0hn3YKuBCOAS0bK8E0wf

# `transformers` meets `bitsandbytes` for democratzing Large Language Models (LLMs) through 4bit quantization

<center>
<img src="https://github.com/huggingface/blog/blob/main/assets/96_hf_bitsandbytes_integration/Thumbnail_blue.png?raw=true" alt="drawing" width="700" class="center"/>
</center>

Welcome to this notebook that goes through the recent `bitsandbytes` integration that includes the work from the [QLoRA paper](https://arxiv.org/abs/2305.14314) that introduces no performance degradation 4bit quantization techniques, for democratizing LLMs inference and training.

In this notebook, we will learn together how to load a model in 4bit, understand all its variants and how to run them for inference. 

[In the training notebook](https://colab.research.google.com/drive/1VoYNfYDKcKRQRor98Zbf2-9VQTtGJ24k?usp=sharing), you will learn how to use 4bit models to fine-tune these models. 

If you liked the previous work for integrating [*LLM.int8*](https://arxiv.org/abs/2208.07339), you can have a look at the [introduction blogpost](https://huggingface.co/blog/hf-bitsandbytes-integration) to lean more about that quantization method.

Note that this could be used for any model that supports `device_map` (i.e. loading the model with `accelerate`) - meaning that this totally agnostic to modalities, you can use it for `Blip2`, etc.

## Download requirements

First, install the dependencies below to get started. As these features are available on the `main` branches only, we need to install the libraries below from source.
"""

# NOTE 需要确保这里的是最新的版本！特别是基于git安装的，需要是dev版本的！
#!pip install -q -U bitsandbytes
#!pip install -q -U git+https://github.com/huggingface/transformers.git
#!pip install -q -U git+https://github.com/huggingface/peft.git
#!pip install -q -U git+https://github.com/huggingface/accelerate.git

"""## Basic usage

Similarly as 8bit models, you can load and convert a model in 8bit by just adding the argument `load_in_4bit`! As simple as that!
Let's first try to load small models, by starting with `facebook/opt-350m`.
"""

from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "facebook/opt-350m"

model = AutoModelForCausalLM.from_pretrained(model_id, 
        load_in_4bit=True, # NOTE 这里最重要了 
        device_map="auto",
        cache_dir='/workspace/asr/Huatuo-Llama-Med-Chinese')

tokenizer = AutoTokenizer.from_pretrained(model_id,
        cache_dir='/workspace/asr/Huatuo-Llama-Med-Chinese')

"""The model conversion technique is totally similar as the one presented in the [8 bit integration blogpost](https://huggingface.co/blog/hf-bitsandbytes-integration) - it is based on module replacement. If you print the model, you will see that most of the `nn.Linear` layers are replaced by `bnb.nn.Linear4bit` layers!"""

print(model)

"""Once loaded, run a prediction as you would do it with a classic model"""

text = "Hello my name is"
device = "cuda:0"

inputs = tokenizer(text, return_tensors="pt").to(device)
outputs = model.generate(**inputs, max_new_tokens=20)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
# Hello my name is jimmy and I am a new member of the reddit clan. I am a new member of
"""## Advaced usages

Let's review in this section advanced usage of the 4bit integration. First, you need to understand the different arguments that can be tweaked and used. 

All these parameters can be changed by using the `BitsandBytesConfig` from `transformers` and pass it to `quantization_config` argument when calling `from_pretrained`.

Make sure to pass `load_in_4bit=True` when using the `BitsAndBytesConfig`!

### Changing the compute dtype

The compute dtype is used to change the dtype that will be used during computation. For example, hidden states could be in `float32` but computation can be set to `bf16` for speedups.
By default, the compute dtype is set to `float32`.
"""

import torch
from transformers import BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16 # NOTE, 缺省如果不指定，那么就是'float32'
)
# cd = compute dtype, 计算的时候的data type，数据类型
model_cd_bf16 = AutoModelForCausalLM.from_pretrained(model_id, 
        quantization_config=quantization_config, # NOTE
        cache_dir='/workspace/asr/Huatuo-Llama-Med-Chinese')

outputs = model_cd_bf16.generate(**inputs, max_new_tokens=20)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
# Hello my name is John and I am a very happy man. I am a very happy man. I am a very
"""### Changing the quantization type

The 4bit integration comes with 2 different quantization types: FP4 and NF4. The NF4 dtype stands for Normal Float 4 and is introduced in the [QLoRA paper](https://arxiv.org/abs/2305.14314)

YOu can switch between these two dtype using `bnb_4bit_quant_type` from `BitsAndBytesConfig`. By default, the FP4 quantization is used.
"""

from transformers import BitsAndBytesConfig

nf4_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4", # NOTE, 缺省状态下，是'FP4'，这里是换成了'nf4'
)

model_nf4 = AutoModelForCausalLM.from_pretrained(model_id, 
        quantization_config=nf4_config, # NOTE
        cache_dir='/workspace/asr/Huatuo-Llama-Med-Chinese')

outputs = model_nf4.generate(**inputs, max_new_tokens=20)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
# Hello my name is jimmy and I am a new member of the reddit clan. I am a new member of
"""### Use nested quantization for more memory efficient inference and training

We also advise users to use the nested quantization technique. This saves more memory at no additional performance - from our empirical observations, this enables fine-tuning llama-13b model on an NVIDIA-T4 16GB with a sequence length of 1024, batch size of 1 and gradient accumulation steps of 4.

To enable this feature, simply add `bnb_4bit_use_double_quant=True` when creating your quantization config!
"""

from transformers import BitsAndBytesConfig

double_quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True, # NOTE 使用双重量化
)

model_double_quant = AutoModelForCausalLM.from_pretrained(model_id, 
        quantization_config=double_quant_config, # NOTE
        cache_dir='/workspace/asr/Huatuo-Llama-Med-Chinese')
'''
ipdb> model_double_quant.lm_head.weight
Parameter containing:
tensor([[-0.0353,  0.0629, -0.0628,  ..., -0.0625,  0.0188,  0.0313],
        [ 0.0213,  0.0379, -0.0625,  ..., -0.0625, -0.0167,  0.0313],
        [-0.0484, -0.0648,  0.0690,  ...,  0.0656, -0.0626, -0.0485],
        ...,
        [ 0.0723,  0.0312, -0.0634,  ..., -0.0625, -0.0053, -0.0755],
        [ 0.0596, -0.0695, -0.0626,  ...,  0.0736, -0.0040,  0.0409],
        [-0.0237,  0.0327, -0.0636,  ..., -0.0625, -0.0248,  0.0315]],
       device='cuda:7', dtype=torch.float16, requires_grad=True)
'''

outputs = model_double_quant.generate(**inputs, max_new_tokens=20)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))

"""### Combining all the features together

Of course, the features are not mutually exclusive. You can combine these features together inside a single quantization config. Let us assume you want to run a model with `nf4` as the quantization type, with nested quantization and using `bfloat16` as the compute dtype:
"""

import torch
from transformers import BitsAndBytesConfig
# bnb = bits and bytes TODO
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True, # NOTE 这是四个参数配置都给加上了，赞啊！
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)

model_4bit = AutoModelForCausalLM.from_pretrained(model_id, 
        quantization_config=bnb_config,
        cache_dir='/workspace/asr/Huatuo-Llama-Med-Chinese')

outputs = model_4bit.generate(**inputs, max_new_tokens=20)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
# Hello my name is John and I am a very happy man. I am a very happy man. I am a very

"""## Pushing the limits of Google Colab

How far can we go using 4bit quantization? We'll see below that it is possible to load a 20B-scale model (40GB in half precision) entirely on the GPU using this quantization method! 🤯

Let's load the model with NF4 quantization type for better results, `bfloat16` compute dtype as well as nested quantization for a more memory efficient model loading.
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

model_id = "EleutherAI/gpt-neox-20b" # TODO 这是换成了200亿参数的大模型了啊！
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True, # NOTE 这是四个配置，都给加上了
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)

tokenizer = AutoTokenizer.from_pretrained(model_id,
        cache_dir='/workspace/asr/Huatuo-Llama-Med-Chinese')

model_4bit = AutoModelForCausalLM.from_pretrained(model_id, 
        quantization_config=bnb_config, device_map="auto",
        cache_dir='/workspace/asr/Huatuo-Llama-Med-Chinese')

"""Let's make sure we loaded the whole model on GPU"""

model_4bit.hf_device_map
# {'gpt_neox.embed_in': 0, 'gpt_neox.layers.0': 0, 'gpt_neox.layers.1': 0, 'gpt_neox.layers.2': 0, 'gpt_neox.layers.3': 1, 'gpt_neox.layers.4': 1, 'gpt_neox.layers.5': 1, 'gpt_neox.layers.6': 1, 'gpt_neox.layers.7': 1, 'gpt_neox.layers.8': 1, 'gpt_neox.layers.9': 1, 'gpt_neox.layers.10': 2, 'gpt_neox.layers.11': 2, 'gpt_neox.layers.12': 2, 'gpt_neox.layers.13': 2, 'gpt_neox.layers.14': 2, 'gpt_neox.layers.15': 2, 'gpt_neox.layers.16': 2, 'gpt_neox.layers.17': 3, 'gpt_neox.layers.18': 3, 'gpt_neox.layers.19': 3, 'gpt_neox.layers.20': 3, 'gpt_neox.layers.21': 3, 'gpt_neox.layers.22': 3, 'gpt_neox.layers.23': 3, 'gpt_neox.layers.24': 4, 'gpt_neox.layers.25': 4, 'gpt_neox.layers.26': 4, 'gpt_neox.layers.27': 4, 'gpt_neox.layers.28': 4, 'gpt_neox.layers.29': 4, 'gpt_neox.layers.30': 4, 'gpt_neox.layers.31': 5, 'gpt_neox.layers.32': 5, 'gpt_neox.layers.33': 5, 'gpt_neox.layers.34': 5, 'gpt_neox.layers.35': 5, 'gpt_neox.layers.36': 5, 'gpt_neox.layers.37': 5, 'gpt_neox.layers.38': 6, 'gpt_neox.layers.39': 6, 'gpt_neox.layers.40': 6, 'gpt_neox.layers.41': 6, 'gpt_neox.layers.42': 6, 'gpt_neox.layers.43': 6, 'gpt_neox.final_layer_norm': 6, 'embed_out': 7}

"""Once loaded, run a generation!"""

text = "Hello my name is"
device = "cuda:0"
inputs = tokenizer(text, return_tensors="pt").to(device)

outputs = model_4bit.generate(**inputs, max_new_tokens=20)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
# Hello my name is john and i am a student at the university of south carolina. i am a member

"""As you can see, we were able to load and run the 4bit gpt-neo-x model entirely on the GPU"""
