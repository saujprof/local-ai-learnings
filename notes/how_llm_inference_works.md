# How an LLM Processes a Prompt Internally

This note captures a practical mental model of what happens inside a decoder-style Transformer during inference.

The goal is not to reproduce every implementation detail, but to understand the core path from text input to next-token prediction.

---

## 1. Start With Text

Example prompt:

```text
Capital of Germany is
```

For simplicity, assume the tokenizer produces exactly four tokens:

```text
T1 = Capital
T2 = of
T3 = Germany
T4 = is
```

Real tokenizers may split words differently.

---

## 2. Tokenization

The model does not process raw text directly.

The tokenizer converts text into tokens, and every token has an ID from the model's vocabulary.

Conceptually:

```text
Capital  -> token ID
of       -> token ID
Germany  -> token ID
is       -> token ID
```

So:

```text
Text
  ↓
Tokenizer
  ↓
Token IDs
```

---

## 3. Token IDs Become Embeddings

The model contains a learned embedding table.

Each token ID selects one row from that table:

```text
token ID
   ↓
embedding lookup
   ↓
vector
```

For a tiny imaginary model:

```text
T1 = [1.0, 0.0]
T2 = [0.0, 1.0]
T3 = [1.0, 1.0]
T4 = [0.0, 2.0]
```

Real models use much larger vectors.

Important distinction:

```text
Token ID
    ↓
integer identifying a vocabulary item

Embedding
    ↓
initial learned vector for that token

Hidden representation
    ↓
updated vector after Transformer processing
```

The token ID stays the same. The hidden representation changes through the layers.

---

## 4. All Prompt Tokens Enter the Transformer

All available prompt-token vectors are processed together.

```text
T1
T2
T3
T4
 ↓
Transformer Layer 1
```

Layer 1 produces:

```text
T1', T2', T3', T4'
```

Layer 2 receives those updated vectors:

```text
T1', T2', T3', T4'
        ↓
     Layer 2
        ↓
T1'', T2'', T3'', T4''
```

Every Transformer layer has the same general architecture, but its own learned weights.

---

## 5. Q, K and V

Inside self-attention, each token is transformed into three vectors:

```text
Q = Query
K = Key
V = Value
```

Each Transformer layer has learned matrices:

```text
Wq
Wk
Wv
```

For token `T1`:

```text
T1 × Wq -> T1Q
T1 × Wk -> T1K
T1 × Wv -> T1V
```

For `T2`, `T3`, and `T4`, the same layer matrices are used.

For one token, Q, K, and V are vectors.

For all tokens together:

```text
Q = matrix of all Query vectors
K = matrix of all Key vectors
V = matrix of all Value vectors
```

A useful intuition:

```text
Query = what information am I looking for?
Key   = what kind of information do I contain?
Value = what information can I contribute?
```

These are learned numeric vectors, not literal English meanings.

---

## 6. Matrix Multiplication vs Dot Product

They are related, but not the same operation.

### Dot product

Two vectors produce one number:

```text
[a, b] · [c, d]
=
a*c + b*d
```

### Matrix multiplication

Matrix multiplication combines many dot products.

For example:

```text
token vector × Wq
```

produces a new Query vector.

So:

```text
vector · vector
    ↓
one number

vector × matrix
    ↓
new vector

matrix × matrix
    ↓
new matrix
```

---

## 7. Attention for T4

Focus on the last prompt token:

```text
T4 = is
```

Its Query vector is:

```text
T4Q
```

Because this is a causal language model, T4 can attend to T1, T2, T3, and T4.

The model computes:

```text
T4Q · T1K -> score 1
T4Q · T2K -> score 2
T4Q · T3K -> score 3
T4Q · T4K -> score 4
```

Each is a dot product, so each result is one number.

Example:

```text
T1 -> 1.2
T2 -> 0.5
T3 -> 3.1
T4 -> 1.7
```

These are raw attention scores.

---

## 8. What is d_k?

`d_k` is the dimensionality of the Key and Query vectors for one attention head.

Example:

```text
T4Q = [0.3, 0.2, 0.9]
```

This has three dimensions:

```text
d_k = 3
```

Attention scores are scaled by:

```text
sqrt(d_k)
```

Conceptually:

```text
Q · K
──────
sqrt(d_k)
```

Scaling keeps dot-product values in a stable range before softmax.

---

## 9. What Softmax Does

Suppose the scaled scores are:

```text
[1.0, 0.2, 2.5, 0.8]
```

Softmax converts them into normalized weights such as:

```text
[0.14, 0.06, 0.67, 0.13]
```

Important properties:

```text
all values are positive
all values sum to 1
```

So they can be interpreted as relative attention weights:

```text
T1 -> 14%
T2 ->  6%
T3 -> 67%
T4 -> 13%
```

---

## 10. Weighted Sum of Values

The attention weights are applied to the Value vectors:

```text
0.14 * T1V
+
0.06 * T2V
+
0.67 * T3V
+
0.13 * T4V
```

Each weight is a scalar.

Example:

```text
0.14 * [1, 2, 3]
=
[0.14, 0.28, 0.42]
```

After adding the weighted Value vectors together, we get one new vector:

```text
AttentionOutput(T4)
```

Useful mental model:

```text
Query
  ↓
compare with Keys
  ↓
attention scores
  ↓
scale
  ↓
softmax
  ↓
attention weights
  ↓
weighted sum of Values
  ↓
contextual information
```

---

## 11. Causal Attention

Future tokens are masked.

For:

```text
T1 = Capital
T2 = of
T3 = Germany
T4 = is
```

the allowed attention is:

```text
T1 -> T1

T2 -> T1, T2

T3 -> T1, T2, T3

T4 -> T1, T2, T3, T4
```

This prevents the model from looking at future tokens while learning or generating.

---

## 12. Multiple Attention Heads

Real models use multiple attention heads.

Conceptually:

```text
Token representation
        ↓
 ┌──────┼──────┐
 ↓      ↓      ↓
Head 1 Head 2 Head 3 ...
 ↓      ↓      ↓
attention outputs
        ↓
 concatenate
        ↓
 output projection
```

Different heads can learn different relationships.

Humans do not manually assign meanings such as:

```text
Head 1 = grammar
Head 2 = nouns
Head 3 = geography
```

Any such specialization is learned, not predefined.

---

## 13. Residual Connection After Attention

The model keeps the previous representation and adds the attention output:

```text
A = T4 + AttentionOutput(T4)
```

Example:

```text
T4                  = [1.0, 2.0, 1.0]
AttentionOutput(T4) = [0.5, 0.8, 0.3]

A                   = [1.5, 2.8, 1.3]
```

This is a residual connection.

---

## 14. MLP / Feed Forward Network

After attention, each token representation passes through an MLP.

MLP means:

```text
Multi-Layer Perceptron
```

Simplified:

```text
token vector
    ↓
linear transformation
    ↓
larger intermediate vector
    ↓
activation / gating
    ↓
linear transformation
    ↓
vector back to model dimension
```

A useful distinction:

```text
Attention
    ↓
mixes / gathers information between tokens

MLP
    ↓
transforms information inside each token representation
```

---

## 15. Second Residual Connection

After the MLP:

```text
A = representation after attention residual

M = MLP(A)

LayerOutput = A + M
```

So a simplified Transformer layer is:

```text
Input
  ↓
Attention
  ↓
Residual add
  ↓
MLP
  ↓
Residual add
  ↓
Output
```

Real models also use normalization around these components. It is omitted here to keep the core mechanism clear.

---

## 16. Repeat Across Layers

Layer 1:

```text
T1, T2, T3, T4
        ↓
attention + residual + MLP + residual
        ↓
T1', T2', T3', T4'
```

Layer 2:

```text
T1', T2', T3', T4'
        ↓
attention + residual + MLP + residual
        ↓
T1'', T2'', T3'', T4''
```

A real LLM may have dozens of Transformer layers.

The representations become increasingly contextualized through the network.

It is too simplistic to say:

```text
Layer 1 = grammar
Layer 2 = nouns
Layer 3 = facts
```

Layers can learn different kinds of features, but they do not have one clean human-assigned job each.

---

## 17. Final Transformer Output

After the final layer, there is still one hidden vector for every prompt position:

```text
T1_final
T2_final
T3_final
T4_final
```

For next-token prediction after:

```text
Capital of Germany is
```

the model uses the final hidden state at the last position:

```text
T4_final
```

This is no longer just the embedding for `is`.

Through attention across many layers, it represents the context available at that position.

---

## 18. Vocabulary Projection

The Transformer does not directly output the word `Berlin`.

It outputs a hidden vector.

The final hidden vector is multiplied by a learned output matrix.

If:

```text
T4_final shape = 1 × hidden_dimension
```

and:

```text
output matrix shape = hidden_dimension × vocabulary_size
```

then:

```text
T4_final × output_matrix
```

produces:

```text
1 × vocabulary_size
```

That is one score for every vocabulary token.

Example:

```text
Berlin -> 7.2
Paris  -> 2.1
London -> 1.4
Rome   -> 0.9
EOS    -> -1.2
```

These raw scores are called:

```text
logits
```

So vocabulary projection means:

```text
final hidden vector
        ↓
matrix multiplication
        ↓
one logit per vocabulary token
```

---

## 19. Logits to Next Token

The logits are converted into a probability distribution.

Conceptually:

```text
Berlin -> 94%
Paris  ->  3%
London ->  1%
Rome   ->  1%
EOS    ->  1%
```

The decoding strategy selects the next token.

Depending on configuration, this can use:

- greedy selection
- temperature
- top-k
- top-p
- other sampling rules

Suppose the selected token is:

```text
Berlin
```

The sequence becomes:

```text
Capital of Germany is Berlin
```

The model then predicts the next token.

---

## 20. Why Does This Work?

During training, the model repeatedly learns:

```text
Given previous tokens,
predict the next token.
```

Example:

```text
Input:
Capital of Germany is

Target:
Berlin
```

If the model gives too much probability to the wrong token, training loss increases.

Backpropagation adjusts learned parameters such as:

- embeddings
- Q/K/V projection matrices
- attention weights
- MLP weights
- output projection
- other model parameters

Across huge amounts of training data, the model learns representations that make plausible next tokens receive higher scores.

---

## 21. How Generation Stops

The vocabulary also contains special tokens that can represent the end of a sequence or assistant turn.

Conceptually:

```text
EOS
```

After:

```text
Capital of Germany is Berlin.
```

the model might assign a high probability to an ending token.

If that token is selected, generation stops.

The runtime/application can also stop generation because of:

- maximum token limits
- stop sequences
- cancellation
- request limits

---

## 22. Prompt Processing vs Generation

There are two useful phases to distinguish.

### Prompt processing

All existing prompt tokens are processed with causal masking:

```text
T1 T2 T3 T4
    ↓
Transformer
```

### Generation

New tokens are produced one at a time:

```text
Capital of Germany is
        ↓
Berlin
        ↓
.
        ↓
EOS
```

Inference runtimes use optimizations such as KV caching so they do not recompute all previous attention information from scratch for every generated token.

---

# Full Mental Model

```text
TEXT
│
▼
TOKENIZER
│
│ token IDs
▼
EMBEDDING LOOKUP
│
│ vectors
▼
════════════════════════════════
      TRANSFORMER LAYER
┌──────────────────────────────┐
│ token × Wq -> Query          │
│ token × Wk -> Key            │
│ token × Wv -> Value          │
│              ↓               │
│ Query · Keys                 │
│              ↓               │
│ divide by sqrt(d_k)          │
│              ↓               │
│ softmax                      │
│              ↓               │
│ attention weights            │
│              ↓               │
│ weighted sum of Values       │
│              ↓               │
│ residual connection          │
│              ↓               │
│ MLP                          │
│              ↓               │
│ residual connection          │
└──────────────────────────────┘
════════════════════════════════
│
▼
NEXT TRANSFORMER LAYER
│
▼
...
│
▼
FINAL HIDDEN STATES
│
▼
TAKE LAST POSITION
│
▼
VOCABULARY PROJECTION
│
▼
LOGITS FOR EVERY VOCAB TOKEN
│
▼
SOFTMAX / DECODING
│
▼
NEXT TOKEN
│
├──────────────► repeat
│
└── EOS / stop condition -> finish
```

---

# Core Ideas to Remember

1. Text is tokenized into token IDs.
2. Token IDs are looked up in the model's learned embedding table.
3. All available prompt-token vectors go through Transformer layers.
4. Every attention layer creates Query, Key, and Value vectors.
5. Query-Key dot products create attention scores.
6. Scores are scaled by `sqrt(d_k)`.
7. Softmax turns scores into attention weights.
8. The weighted sum of Value vectors creates contextual information.
9. Residual connections preserve and add information.
10. The MLP further transforms each token representation.
11. This repeats through all Transformer layers.
12. The final hidden state at the last prompt position is used for next-token prediction.
13. Vocabulary projection creates one logit per vocabulary token.
14. Decoding selects the next token.
15. The token is appended and generation repeats until an end token or runtime stop condition.

---

## One-Sentence Summary

> An LLM repeatedly transforms token vectors through attention and neural-network layers until the final context representation can be projected into scores for the next token in its vocabulary.
