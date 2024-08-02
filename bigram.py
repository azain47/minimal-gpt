import torch
import torch.nn as nn
from torch.nn import functional as F

# hyperparameters
batch_size = 32 # how many independent sequences will we process in parallel?
block_size = 8 # what is the maximum context length for predictions?
max_iters = 3000
eval_interval = 300
learning_rate = 1e-2
device = 'cuda' if torch.cuda.is_available() else 'cpu'
eval_iters = 200
# ------------

with open('shakespeare.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# here are all the unique characters that occur in this text
chars = sorted(list(set(text)))
vocab_size = len(chars)

# encoder decoder / tokenizer 
stoi = {ch:i for i,ch in enumerate(chars)} # simple mapping from set of unique chars
itos = {i:ch for i,ch in enumerate(chars)}

encode = lambda s: [stoi[c] for c in s]  # encode function to lookup the stoi dict
decode = lambda i: ''.join([itos[x] for x in i])  #decode func to lookup the itos dict

# dataset creation
data = torch.tensor(encode(text), dtype=torch.long)

# Also split the dataset into train-val
n = int(0.9 * len(data))  # 90-10 split
train_data = data[:n]
val_data = data[n:]

# Batching of dataset
# The dataset is divided on basis of 2 dimensions. Time Dimension and Batch Size.
# Time dimension is basically the context length. How many tokens our model sees before it predicts the next token.
# Karpathy says it as block_size.
# The Batch Dimension or Batch size is just no. of independent sequences the model will train on parallely(right word?)
# basically the batch size in a mini batch gradient descent, nothing else.

def get_batch(split):
    # generate a mini batch of inputs, targets
    data = train_data if split=='train' else val_data
    ix = torch.randint(len(data) - batch_size, (batch_size,))
    x = torch.stack([data[i:block_size+i] for i in ix]).to(device)
    y = torch.stack([data[i+1:block_size+i+1] for i in ix]).to(device)
    return x,y

@torch.no_grad()
def estimate_loss():
    out = {}
    model.eval()
    for split in ['train', 'val']:
        losses = torch.zeros(eval_iters)
        for k in range(eval_iters):
            X, Y = get_batch(split)
            logits, loss = model(X, Y)
            losses[k] = loss.item()
        out[split] = losses.mean()
    model.train()
    return out


class BigramLM(nn.Module):
    def __init__(self, vocab_size):
        super().__init__()
        # directly reads off the probability for next token 
        self.token_embedding_table = nn.Embedding(vocab_size, vocab_size)

    def forward(self, idx, targets = None):

        # idx and targets are both (B,T) tensor of integers
        logits = self.token_embedding_table(idx) # (B,T,C)

        if targets is None:
            loss = None
        else:
            B, T, C = logits.shape
            logits = logits.view(B*T, C)
            targets = targets.view(B*T)
            loss = F.cross_entropy(logits, targets)

        return logits, loss

    def generate(self, idx, max_new_tokens):
        # idx is (B, T) array of indices in the current context
        for _ in range(max_new_tokens):
            # get the predictions
            logits, loss = self(idx)
            # focus only on the last time step
            logits = logits[:, -1, :] # becomes (B, C)
            # apply softmax to get probabilities
            probs = F.softmax(logits, dim=-1) # (B, C)
            # sample from the distribution
            idx_next = torch.multinomial(probs, num_samples=1) # (B, 1)
            # append sampled index to the running sequence
            idx = torch.cat((idx, idx_next), dim=1) # (B, T+1)
        return idx
    
model = BigramLM(vocab_size).to(device)


# Training the model
optim = torch.optim.AdamW(model.parameters(), lr=1e-3)

for iter in range(max_iters):

    # every once in a while evaluate the loss on train and val sets
    if iter % eval_interval == 0:
        losses = estimate_loss()
        print(f"step {iter}: train loss {losses['train']:.4f}, val loss {losses['val']:.4f}")

    # sample a batch of data
    xb, yb = get_batch('train')

    # evaluate the loss
    logits, loss = model(xb, yb)
    optim.zero_grad(set_to_none=True)
    loss.backward()
    optim.step()

# generate from the model
context = torch.zeros((1, 1), dtype=torch.long, device=device)
print(decode(model.generate(context, max_new_tokens=500)[0].tolist()))