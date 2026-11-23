#!/usr/bin/env python3
"""
Rebalance Pages Script for CLTML IEEE Research Paper
====================================================
Rebalances all 8 pages of the IEEE conference paper:
- Sets explicit height: X.Xin and width: auto on all figures to prevent aspect-ratio layout overflow
- Removes gray borders around figures
- Strips dangling </div> from s5b so footer 7 is strictly inside the page container
- Verifies exact div balance (opens == closes) on every page
- Page 3: Table I, Sec II-E, Sec II-F, Sec III (A, B, C, D)
- Page 4: Table II, Sec IV (A, B)
- Page 5: Fig. 2 (top full-width span), Sec IV (C, D, E, F)
- Page 6: Table III, Table IV, Sec IV (G, H), Sec V-A
- Page 7: Fig. 3, Table V, Table VI, Sec V-B
- Page 8: Fig. 4, Sec V-C, V-D, V-E, VI, and References [1]-[36]
"""

import os
import re

def rebalance():
    template_path = "paper/Review_Paper_IEEE.html.template"
    backup_path = "paper/Review_Paper_IEEE.html.template.bak"
    with open(backup_path, "r", encoding="utf-8") as f:
        src = f.read()

    # Normalize CSS
    src = src.replace("border: 0.3pt solid #ccc;", "border: none;")
    src = src.replace("border: 0.5pt solid #ccc;", "border: none;")
    src = src.replace("border: 1px solid #ccc;", "border: none;")

    # Fix .figure-img CSS
    src = re.sub(
        r'\.figure-img\s*\{[^}]*\}',
        '''.figure-img {
    height: auto;
    max-width: 100%;
    object-fit: contain;
    border: none;
    display: block;
    margin: 0 auto 3px auto;
}''',
        src
    )

    # Adjust equation 4 font size and nowrap
    src = re.sub(
        r'<div class="eq-math"[^>]*>&forall;<em>t</em>.*?&not;<span class="op">CanSleep</span>\(<span class="op">Primitive</span>\(<em>t</em>\)\)</div>',
        '<div class="eq-math" style="font-size: 7.2pt; white-space: nowrap;">&forall;<em>t</em>, &nbsp; <span class="op">Context</span>(<em>t</em>) &isin; {<span class="op">HARDIRQ, SOFTIRQ, RCU_READ</span>} &rArr; &not;<span class="op">CanSleep</span>(<span class="op">Primitive</span>(<em>t</em>))</div>',
        src
    )

    # Extract pages
    parts = src.split("<!-- PAGE ")
    preamble = parts[0]
    p1 = parts[1].split("\n", 1)[1]
    p2 = parts[2].split("\n", 1)[1]
    p3 = parts[3].split("\n", 1)[1]
    p4 = parts[4].split("\n", 1)[1]
    p5 = parts[5].split("\n", 1)[1]
    p6 = parts[6].split("\n", 1)[1]
    p7 = parts[7].split("\n", 1)[1]
    p8 = parts[8].split("\n", 1)[1]

    p8_content = p8.rsplit("</body>", 1)[0]

    # Extract components
    # Page 3
    t1 = re.search(r'(<div class="table-span">\s*<div class="table-caption">Table I:.*?</table>\s*</div>)', p3, re.DOTALL).group(1)
    s2ef = re.search(r'(<h3 class="subsec-heading"[^>]*>E\. Dynamic Heuristics.*?)(?=</div>\s*<div class="running-footer">3)', p3, re.DOTALL).group(1)

    # Page 4
    t2 = re.search(r'(<div class="table-span">\s*<div class="table-caption">Table II:.*?</table>\s*</div>)', p4, re.DOTALL).group(1)
    s3 = re.search(r'(<h2 class="sec-heading">III\. Related Work.*?)(?=</div>\s*<div class="running-footer">4)', p4, re.DOTALL).group(1)

    # Page 5
    s4ab = re.search(r'(<h2 class="sec-heading"[^>]*>IV\. The CLTML Architecture.*?)(?=<div class="figure-container">|<div class="figure-span">)', p5, re.DOTALL).group(1)
    fig2 = re.search(r'(<div class="figure-(?:container|span)">\s*<img src="\[\[FIG2_BASE64\]\]".*?</div>\s*</div>)', p5, re.DOTALL).group(1)
    fig2 = re.sub(r'class="figure-container"', 'class="figure-span"', fig2)
    fig2 = re.sub(r'style="[^"]*"', 'style="height: 1.80in; width: auto;"', fig2)
    s4cd = re.search(r'(<h3 class="subsec-heading">C\. Formal Synchronization Contract.*?)(?=</div>\s*<div class="running-footer">5)', p5, re.DOTALL).group(1)

    # Page 6
    s4ef = re.search(r'(<h3 class="subsec-heading"[^>]*>E\. Freestanding Kernel C LUT Implementation.*?)(?=<h3 class="subsec-heading">G\. Scalable Per-CPU)', p6, re.DOTALL).group(1)
    s4gh = re.search(r'(<h3 class="subsec-heading">G\. Scalable Per-CPU.*?)(?=<div class="table-span">\s*<div class="table-caption">Table III:)', p6, re.DOTALL).group(1)
    t3 = re.search(r'(<div class="table-span">\s*<div class="table-caption">Table III:.*?</table>\s*</div>)', p6, re.DOTALL).group(1)

    # Page 7
    t4 = re.search(r'(<div class="table-span">\s*<div class="table-caption">Table IV:.*?</table>\s*</div>)', p7, re.DOTALL).group(1)
    fig3 = re.search(r'(<div class="figure-span">\s*<img src="\[\[FIG3_BASE64\]\]".*?</div>\s*</div>)', p7, re.DOTALL).group(1)
    fig3 = re.sub(r'style="[^"]*"', 'style="height: 1.55in; width: auto;"', fig3)
    s5a = re.search(r'(<h2 class="sec-heading"[^>]*>V\. Experimental Evaluation.*?)(?=<h3 class="subsec-heading">B\. Userspace 4-Lock)', p7, re.DOTALL).group(1)
    s5b = re.search(r'(<h3 class="subsec-heading">B\. Userspace 4-Lock.*?)(?=<div class="table-span"[^>]*>\s*<div class="table-caption">Table V:)', p7, re.DOTALL).group(1)
    t5 = re.search(r'(<div class="table-span"[^>]*>\s*<div class="table-caption">Table V:.*?</table>\s*</div>)', p7, re.DOTALL).group(1)
    t6 = re.search(r'(<div class="table-span"[^>]*>\s*<div class="table-caption">Table VI:.*?</table>\s*</div>)', p7, re.DOTALL).group(1)

    # Strip trailing </div> from s5b
    s5b = s5b.rstrip()
    if s5b.endswith('</div>'):
        s5b = s5b[:-6].rstrip()

    # Compact table paddings for Table 5 and Table 6 so they easily fit
    t5 = re.sub(r'style="margin:[^"]*"', 'style="margin: 2px 0 1px 0;"', t5)
    t6 = re.sub(r'style="margin:[^"]*"', 'style="margin: 2px 0 1px 0;"', t6)

    # Page 8
    fig4 = re.search(r'(<div class="figure-span">\s*<img src="\[\[FIG4_BASE64\]\]".*?</div>\s*</div>)', p8_content, re.DOTALL).group(1)
    fig4 = re.sub(r'style="[^"]*"', 'style="height: 1.50in; width: auto;"', fig4)
    s8 = re.search(r'(<h3 class="subsec-heading"[^>]*>C\. Distribution Shift.*?)(?=</div>\s*<div class="running-footer">8)', p8_content, re.DOTALL).group(1)

    # Also update Fig 1 on Page 2
    p2 = re.sub(r'style="max-height:\s*[^;]+;"', 'style="height: 1.45in; width: auto;"', p2)

    # Build new pages
    new_p1 = f"""<!-- PAGE 1 -->
{p1.strip()}"""

    new_p2 = f"""<!-- PAGE 2 -->
{p2.strip()}"""

    new_p3 = f"""<!-- PAGE 3 -->
<div class="page">
    <div class="running-header">
        <span>CHANDRU G AND CHETHAN S: COMPILE-TIME LOOKUP TABLES FOR KERNEL LOCK SELECTION</span>
        <span>IEEE TRANSACTIONS / CONFERENCE FORMAT</span>
    </div>

    {t1}

    <div class="cols">
        {s2ef}

        {s3}
    </div>
    <div class="running-footer">3</div>
</div>"""

    new_p4 = f"""<!-- PAGE 4 -->
<div class="page">
    <div class="running-header">
        <span>CHANDRU G AND CHETHAN S: COMPILE-TIME LOOKUP TABLES FOR KERNEL LOCK SELECTION</span>
        <span>IEEE TRANSACTIONS / CONFERENCE FORMAT</span>
    </div>

    {t2}

    <div class="cols">
        {s4ab}
    </div>
    <div class="running-footer">4</div>
</div>"""

    new_p5 = f"""<!-- PAGE 5 -->
<div class="page">
    <div class="running-header">
        <span>CHANDRU G AND CHETHAN S: COMPILE-TIME LOOKUP TABLES FOR KERNEL LOCK SELECTION</span>
        <span>IEEE TRANSACTIONS / CONFERENCE FORMAT</span>
    </div>

    {fig2}

    <div class="cols">
        {s4cd}

        {s4ef}
    </div>
    <div class="running-footer">5</div>
</div>"""

    # Page 6: Table III, Table IV at top, then cols: s4gh, s5a
    new_p6 = f"""<!-- PAGE 6 -->
<div class="page">
    <div class="running-header">
        <span>CHANDRU G AND CHETHAN S: COMPILE-TIME LOOKUP TABLES FOR KERNEL LOCK SELECTION</span>
        <span>IEEE TRANSACTIONS / CONFERENCE FORMAT</span>
    </div>

    {t3}

    {t4}

    <div class="cols">
        {s4gh}

        {s5a}
    </div>
    <div class="running-footer">6</div>
</div>"""

    # Page 7: Fig 3, Table V, Table VI, then cols: s5b
    new_p7 = f"""<!-- PAGE 7 -->
<div class="page">
    <div class="running-header">
        <span>CHANDRU G AND CHETHAN S: COMPILE-TIME LOOKUP TABLES FOR KERNEL LOCK SELECTION</span>
        <span>IEEE TRANSACTIONS / CONFERENCE FORMAT</span>
    </div>

    {fig3}

    {t5}

    {t6}

    <div class="cols">
        {s5b}
    </div>
    <div class="running-footer">7</div>
</div>"""

    new_p8 = f"""<!-- PAGE 8 -->
<div class="page">
    <div class="running-header">
        <span>CHANDRU G AND CHETHAN S: COMPILE-TIME LOOKUP TABLES FOR KERNEL LOCK SELECTION</span>
        <span>IEEE TRANSACTIONS / CONFERENCE FORMAT</span>
    </div>

    {fig4}

    <div class="cols">
        {s8}
    </div>
    <div class="running-footer">8</div>
</div>"""

    pages = [new_p1, new_p2, new_p3, new_p4, new_p5, new_p6, new_p7, new_p8]
    for idx, p in enumerate(pages, 1):
        o = p.count("<div")
        c = p.count("</div>")
        print(f"Page {idx} div balance: opens={o}, closes={c}, diff={o-c}")
        if o != c:
            raise ValueError(f"Page {idx} has unbalanced div tags! opens={o}, closes={c}")

    new_full_html = f"""{preamble.strip()}

{new_p1}

{new_p2}

{new_p3}

{new_p4}

{new_p5}

{new_p6}

{new_p7}

{new_p8}

</body>
</html>
"""

    with open(template_path, "w", encoding="utf-8") as f:
        f.write(new_full_html)

    print("Rebalanced template written to paper/Review_Paper_IEEE.html.template successfully.")

if __name__ == "__main__":
    rebalance()
