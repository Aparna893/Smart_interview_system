import json
import matplotlib.pyplot as plt

# Latest checkpoint path
state_path = (
    "models/answer_checkpoints/"
    "checkpoint-4500/trainer_state.json"
)

# Load trainer state
with open(state_path, "r") as f:

    state = json.load(f)

log_history = state["log_history"]

train_steps = []
train_losses = []

eval_steps = []
eval_losses = []

# Extract logs
for log in log_history:

    if "loss" in log:

        train_steps.append(log["step"])

        train_losses.append(log["loss"])

    if "eval_loss" in log:

        eval_steps.append(log["step"])

        eval_losses.append(log["eval_loss"])

# Optional: remove first spike
train_steps = train_steps[1:]
train_losses = train_losses[1:]

# Plot graph
plt.figure(figsize=(10, 5))

plt.plot(
    train_steps,
    train_losses,
    marker='o',
    label="Training Loss"
)

plt.plot(
    eval_steps,
    eval_losses,
    marker='o',
    label="Validation Loss"
)

plt.xlabel("Steps")

plt.ylabel("Loss")

plt.title(
    "FLAN-T5 Answer Generation Loss Curve"
)

plt.legend()

plt.grid(True)

# Save graph
plt.savefig(
    "models/answer_loss_curve.png"
)

plt.show()

print(
    "Answer loss curve saved at:"
)

print(
    "models/answer_loss_curve.png"
)