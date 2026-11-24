"""Offline, explainable classification against user-owned destination folders."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from math import log, sqrt
from pathlib import Path


SUBJECT_HINTS = {
    "MATEMATICA": ["matematica", "aritmetica", "algebra", "geometria", "calculo", "estatistica", "estatistica basica", "probabilidade"],
    "METODO PARA PRODUCAO DE TRABALHOS CIENTIFICOS": ["metodo para producao de trabalhos cientificos", "metodologia cientifica", "trabalho cientifico", "abnt", "referencias bibliograficas", "citacao", "pesquisa cientifica"],
    "ETICA E CIDADANIA": ["etica", "cidadania", "sociedade", "direitos humanos"],
    "IA NA PRATICA": ["ia na pratica", "inteligencia artificial", "ia generativa"],
    "LEITURA E PRODUÇÃO DE TEXTO": ["leitura e producao de texto", "producao textual", "linguagem", "generos textuais"],
    "PENSAMENTO COMPUTACIONAL": ["pensamento computacional", "algoritmo", "decomposicao", "abstracao"],
    "Guitarra": ["guitarra", "violao", "acorde", "escala musical", "tablatura"],
    "DEV": ["desenvolvimento de software", "programacao", "python", "codigo fonte", "arquitetura de software", "api"],
    "Pessoal": ["documento pessoal", "identidade", "cpf", "rg", "certidao", "passaporte", "laudo", "pericia"],
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    return "".join(c for c in value if not unicodedata.combining(c)).lower()


def terms(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]{3,}", normalize(value))


def subject_names(root: Path) -> list[str]:
    excluded = {"triagem", "ja no drive", "atividades"}
    names = [p.name for p in root.iterdir() if p.is_dir() and normalize(p.name) not in excluded]
    for name in ("Matemática", "Método para Produção de Trabalhos Científicos"):
        if normalize(name) not in {normalize(n) for n in names}:
            names.append(name)
    return sorted(names, key=normalize)


def classify_kind(filename: str, text: str) -> dict:
    """Recognize a broad context before matching any subject folder."""
    name = normalize(Path(filename).stem.replace("_", " ").replace("-", " "))
    head = normalize(text[:6000])
    sample = f"{name} {head[:2500]}"
    academic = [term for term in ("univesp", "universidade", "disciplina", "atividade avaliativa", "semana letiva", "professor", "tutor", "matricula") if term in sample]
    prompts = [term for term in ("prompt mestre", "prompts mestres", "claude", "chatgpt", "engenharia de prompt") if term in sample]
    if prompts and not academic:
        return {"kind": "Desenvolvimento", "suggestion": "DEV/Prompts e IA", "evidence": "tema de prompts e ferramentas de IA: " + ", ".join(prompts[:3]), "new_folder": True}
    if not academic and any(term in sample for term in ("matematica", "aritmetica", "algebra", "metodologia cientifica", "pensamento computacional", "etica e cidadania", "leitura e producao de texto")):
        academic = ["tema de disciplina"]
    if academic:
        return {"kind": "Faculdade", "suggestion": "", "evidence": "contexto acadêmico: " + ", ".join(academic[:3]), "new_folder": False}
    if any(term in sample for term in ("cpf", "passaporte", "certidao", "documento pessoal", "comprovante de residencia")):
        return {"kind": "Pessoal", "suggestion": "Pessoal", "evidence": "documento pessoal", "new_folder": False}
    if any(term in sample for term in ("guitarra", "tablatura", "acorde", "escala musical")):
        return {"kind": "Música", "suggestion": "Guitarra", "evidence": "conteúdo de guitarra", "new_folder": False}
    if any(term in sample for term in ("codigo fonte", "programacao", "desenvolvimento de software", "python", "github")):
        return {"kind": "Desenvolvimento", "suggestion": "DEV", "evidence": "conteúdo de desenvolvimento", "new_folder": False}
    return {"kind": "Indefinido", "suggestion": "", "evidence": "contexto insuficiente", "new_folder": False}


STOP_WORDS = set("para como sobre entre onde quando este esta esse essa aquele aquela muitos muito todos todas pelos pelas uma uns das dos que com sem nao mais menos seu sua seus suas curso aula material pagina capitulo univesp universidade ensino texto trabalho atividade semana modulo professor aluno turma documento escola educacao nome data pdf www https org com book ebook caso cada dados tabela fato artigo resultado resultados federal empresas with their what more from this that there and the marcos aurelio ferreira miranda conclusao certificado grupo individual template modelo resposta respostas exemplo exemplos".split())


def keywords(value: str) -> Counter:
    return Counter(word for word in terms(value[:8000]) if len(word) >= 4 and not word.isdigit() and word not in STOP_WORDS)


class FolderModel:
    """Small local model trained only on PDFs already placed in subject folders."""

    def __init__(self, examples: list[tuple[str, str]], subjects: list[str]):
        counts = {name: Counter() for name in subjects}
        document_counts = Counter()
        for subject, text in examples:
            if subject not in counts or normalize(subject) == "pessoal":
                continue
            words = keywords(text)
            if not words:
                continue
            document_counts[subject] += 1
            counts[subject].update({word: min(count, 3) for word, count in words.items()})
        eligible = {name: counter for name, counter in counts.items() if document_counts[name] >= 2}
        document_frequency = Counter()
        for counter in eligible.values():
            document_frequency.update(counter.keys())
        size = len(eligible)
        self.vectors = {}
        self.norms = {}
        for name, counter in eligible.items():
            vector = {word: (1 + log(count)) * (1 + log((size + 1) / (document_frequency[word] + 1)))
                      for word, count in counter.items()}
            self.vectors[name] = vector
            self.norms[name] = sqrt(sum(weight * weight for weight in vector.values()))

    def suggest(self, text: str) -> list[tuple[str, float, list[str]]]:
        query = keywords(text)
        ranked = []
        for name, vector in self.vectors.items():
            overlap = {word: min(count, 3) * vector[word] for word, count in query.items() if word in vector}
            if len(overlap) < 3:
                continue
            score = sum(overlap.values()) / (sqrt(sum(count * count for count in query.values())) * self.norms[name])
            ranked.append((name, score, sorted(overlap, key=overlap.get, reverse=True)[:5]))
        return sorted(ranked, key=lambda row: row[1], reverse=True)


def classify(filename: str, text: str, subjects: list[str], current_folder: str = "") -> dict:
    """Return ranked suggestions with evidence; never infer that a file is safe to move."""
    filename_n = normalize(Path(filename).stem.replace("_", " ").replace("-", " "))
    cleaned = re.sub(r"\baritm\s+etica\b", "aritmetica", normalize(text[:20000]))
    head = cleaned[:5000]
    body = cleaned[5000:]
    scores = defaultdict(float)
    evidence = defaultdict(list)
    for subject in subjects:
        aliases = [subject]
        for key, hints in SUBJECT_HINTS.items():
            if normalize(key) == normalize(subject):
                aliases.extend(hints)
        for alias in dict.fromkeys(normalize(a) for a in aliases):
            if not alias:
                continue
            pattern = re.compile(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])")
            if pattern.search(filename_n):
                scores[subject] += 10
                evidence[subject].append(f"nome: {alias}")
            if pattern.search(head[:800]):
                scores[subject] += 9 if len(alias.split()) > 1 else 5
                evidence[subject].append(f"capa: {alias}")
            elif pattern.search(head):
                scores[subject] += 6 if len(alias.split()) > 1 else 3
                evidence[subject].append(f"início: {alias}")
            elif len(alias.split()) > 1 and pattern.search(body):
                scores[subject] += 2
                evidence[subject].append(f"texto: {alias}")
    ranked = sorted(((name, round(scores[name], 2)) for name in subjects), key=lambda x: (-x[1], normalize(x[0])))
    ranked = [pair for pair in ranked if pair[1] > 0]
    best = ranked[0] if ranked else ("", 0)
    second = ranked[1] if len(ranked) > 1 else ("", 0)
    return {
        "suggestion": best[0],
        "score": best[1],
        "alternative": second[0],
        "alternative_score": second[1],
        "needs_review": best[1] < 6 or best[1] - second[1] < 5 or not text.strip(),
        "evidence": evidence[best[0]][:8] if best[0] else [],
        "current_folder": current_folder,
    }
