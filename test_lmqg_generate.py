from lmqg import TransformersQG

model = TransformersQG(
    "lmqg/t5-small-squad-qg"
)

context = """
Python is a high-level programming language widely used for web development,
data science, automation, and artificial intelligence. Python supports
object-oriented programming concepts such as inheritance, polymorphism,
encapsulation, and abstraction. Decorators are used to modify the behavior
of functions, while generators use the yield keyword to produce values lazily.
Python also supports exception handling using try-except blocks.
"""

questions = model.generate_q(
    context
)

print("\nGenerated Questions:\n")

print(questions)