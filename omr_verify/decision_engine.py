from dataclasses import dataclass

@dataclass
class Decision:
    action: str
    confidence: float
    reason: str

def decide(source_count, homr_count, distance=None):
    if source_count <= 0:
        return Decision("REVIEW", 0.0, "source symbol detection unavailable")

    ratio = homr_count / source_count

    if distance is not None and distance <= 12 and 0.85 <= ratio <= 1.15:
        return Decision("AUTO", 0.98, "count and position agree")

    if 0.90 <= ratio <= 1.10:
        return Decision("AUTO", 0.90, "symbol count agrees")

    return Decision("REVIEW", 0.0, "uncertain correspondence")
