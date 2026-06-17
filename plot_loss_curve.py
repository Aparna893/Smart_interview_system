import json
import matplotlib.pyplot as plt

# Trainer state file
state_path = "models/checkpoints/checkpoint-2808/trainer_state.json"

# Load logs
with open(state_path, "r") as f:
    state = json.load(f)

log_history = state["log_history"]

train_steps = []
train_losses = []

eval_steps = []
eval_losses = []

# Extract losses
for log in log_history:

    if "loss" in log:
        train_steps.append(log["step"])
        train_losses.append(log["loss"])

    if "eval_loss" in log:
        eval_steps.append(log["step"])
        eval_losses.append(log["eval_loss"])

# Plot graph
plt.figure(figsize=(10, 5))

plt.plot(
    train_steps,
    train_losses,
    label="Training Loss",
    marker='o'
)

plt.plot(
    eval_steps,
    eval_losses,
    label="Validation Loss",
    marker='o'
)

plt.xlabel("Steps")
plt.ylabel("Loss")

plt.title("FLAN-T5 Training vs Validation Loss")

plt.legend()

plt.grid(True)

# Save graph
plt.savefig("models/loss_curve.png")

plt.show()

print("Loss curve saved at models/loss_curve.png")