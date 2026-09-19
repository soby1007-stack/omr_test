import math

def dist(a,b):
    return math.hypot(a["x"]-b["x"], a["y"]-b["y"])

def match(source, homr, radius=45):
    pairs=[]
    used=set()

    for h in homr:
        best=None
        bestd=radius

        for i,s in enumerate(source):
            if i in used:
                continue
            d=dist(s,h)
            if d < bestd:
                bestd=d
                best=i

        if best is not None:
            used.add(best)
            pairs.append({
                "source_index":best,
                "homr":h,
                "source":source[best],
                "distance":round(bestd,2)
            })

    return pairs

def confidence(pairs, source_count, homr_count):
    if not source_count or not homr_count:
        return 0.0

    coverage=len(pairs)/max(source_count,homr_count)

    if not pairs:
        return 0.0

    avg=sum(x["distance"] for x in pairs)/len(pairs)

    pos=max(0.0,1.0-avg/45.0)

    return round(0.55*coverage + 0.45*pos,3)
