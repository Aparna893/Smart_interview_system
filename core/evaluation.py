from ast import keyword
import re
from typing_extensions import final

from nltk.corpus import wordnet

from sklearn.feature_extraction.text import (
    TfidfVectorizer
)

from sklearn.metrics.pairwise import (
    cosine_similarity
)


# -----------------------------------------
# CLEAN TEXT
# -----------------------------------------

def clean_text(text):

    text = text.lower()

    text = re.sub(
        r'[^a-zA-Z0-9\s]',
        '',
        text
    )

    return text


# -----------------------------------------
# KEYWORDS
# -----------------------------------------

def extract_keywords(text):

    words = clean_text(text).split()

    return set(words)


# -----------------------------------------
# SYNONYMS
# -----------------------------------------

def get_synonyms(word):

    try:

        synonyms = set()

        for syn in wordnet.synsets(word):

            for lemma in syn.lemmas():

                synonyms.add(
                    lemma.name().lower()
                )

        return synonyms

    except Exception as e:

        print(
            "WordNet error:",
            e
        )

        return set()

# -----------------------------------------
# KEYWORD + SYNONYM SCORE
# -----------------------------------------

def keyword_score(
    expected_answer,
    candidate_answer
):

    expected_keywords = extract_keywords(
        expected_answer
    )

    candidate_keywords = extract_keywords(
        candidate_answer
    )

    matched = 0

    for word in expected_keywords:

        if word in candidate_keywords:

            matched += 1

        else:

            synonyms = get_synonyms(word)

            if synonyms.intersection(
                candidate_keywords
            ):

                matched += 1

    if len(expected_keywords) == 0:

        return 0

    return (
        matched / len(expected_keywords)
    ) * 100


# -----------------------------------------
# COSINE SIMILARITY
# -----------------------------------------

def semantic_score(
    expected_answer,
    candidate_answer
):
    expected_answer = expected_answer.strip()

    candidate_answer = candidate_answer.strip()

    # ---------------------------------
    # EMPTY TEXT SAFETY
# ---------------------------------

    if (
        not expected_answer
        or

        not candidate_answer
    ):

            return 0
    texts = [
        expected_answer,
        candidate_answer
    ]

    vectorizer = TfidfVectorizer()

    tfidf = vectorizer.fit_transform(
        texts
    )

    similarity = cosine_similarity(
        tfidf[0:1],
        tfidf[1:2]
    )[0][0]

    return similarity * 100


# -----------------------------------------
# FINAL SCORE
# -----------------------------------------

def calculate_final_score(
    expected_answer,
    candidate_answer
):
    if not candidate_answer.strip():

        return {

            "keyword_score": 0,

            "semantic_score": 0,

            "final_score": 0,

            "verdict": "No Answer"
        }
    keyword = keyword_score(
        expected_answer,
        candidate_answer
    )

    semantic = semantic_score(
        expected_answer,
        candidate_answer
    )

    length_penalty = 1

    candidate_word_count = len(
        candidate_answer.split()
    )

    if candidate_word_count < 5:

        length_penalty = 0.6

    elif candidate_word_count < 10:

        length_penalty = 0.8

    final = (
        (
            keyword * 0.5
            +
            semantic * 0.5
        )
        *
        length_penalty
    )
    final = round(final, 2)

    if final >= 80:

        verdict = "Excellent"

    elif final >= 60:

        verdict = "Good"

    elif final >= 40:

        verdict = "Average"

    else:

        verdict = "Poor"

    return {

        "keyword_score":
            round(keyword, 2),

        "semantic_score":
            round(semantic, 2),

        "final_score":
            final,

        "verdict":
            verdict
    }