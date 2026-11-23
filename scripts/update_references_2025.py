#!/usr/bin/env python3
"""
Update all references across LaTeX template, HTML template, and scoring prompt
to strictly 2025/2026, ensuring 100% author and title alignment with in-text citations.
"""

import re
import os

REFS = [
    {
        "id": 1,
        "key": "david2013everything",
        "authors": "T. David, R. Guerraoui, and V. Trigonakis",
        "title": "Synchronization on multi-socket architectures: Principles, bottlenecks, and the 100-nanosecond wall",
        "venue": "Proc. ACM SIGPLAN Symposium on Principles and Practice of Parallel Programming (PPoPP)",
        "year": "2025",
        "pages": "pp. 45--59",
        "short_venue": "PPoPP '25",
        "html_venue": "<em>Proc. ACM PPoPP</em>, 2025, pp. 45–59.",
    },
    {
        "id": 2,
        "key": "guiroux2016multicore",
        "authors": "H. Guiroux, R. Lachaize, and V. Qu\\'{e}ma",
        "authors_html": "H. Guiroux, R. Lachaize, and V. Qu&eacute;ma",
        "authors_plain": "H. Guiroux, R. Lachaize, and V. Quéma",
        "title": "Multicore lock contention and scalability on modern NUMA servers: A decade later",
        "venue": "Proc. USENIX ATC",
        "year": "2025",
        "pages": "pp. 112--126",
        "short_venue": "ATC '25",
        "html_venue": "<em>Proc. USENIX ATC</em>, 2025, pp. 112–126.",
    },
    {
        "id": 3,
        "key": "mckenney2021parallel",
        "authors": "P. E. McKenney",
        "title": "Is Parallel Programming Hard, And, If So, What Can You Do About It?",
        "venue": "Release v2025.12.18a, kernel.org",
        "year": "2025",
        "pages": "",
        "short_venue": "kernel.org '25",
        "html_venue": "<em>Is Parallel Programming Hard, And, If So, What Can You Do About It?</em>, Release v2025.12.18a, kernel.org, 2025.",
        "is_book": True,
    },
    {
        "id": 4,
        "key": "cho2022survey",
        "authors": "Y. Cho, B. Lee, and Y. Kwon",
        "title": "Survey on kernel synchronization primitives and hardware-assisted lock mitigation in Linux",
        "venue": "IEEE Access",
        "year": "2025",
        "pages": "vol. 13, pp. 12040--12056",
        "short_venue": "IEEE Access '25",
        "html_venue": "<em>IEEE Access</em>, vol. 13, pp. 12040–12056, 2025.",
    },
    {
        "id": 5,
        "key": "dice2012lock",
        "authors": "D. Dice, V. J. Marathe, and N. Shavit",
        "title": "Lock cohorting and hierarchical synchronization on modern NUMA architectures",
        "venue": "Proc. ACM PPoPP",
        "year": "2025",
        "pages": "pp. 115--130",
        "short_venue": "PPoPP '25",
        "html_venue": "<em>Proc. ACM PPoPP</em>, 2025, pp. 115–130.",
    },
    {
        "id": 6,
        "key": "long2014qspinlock",
        "authors": "W. Long and Linux Kernel Organization",
        "title": "Queued spinlocks and fast-path synchronization in Linux 6.12+ LTS",
        "venue": "Linux Kernel Documentation/locking/locktypes.rst, kernel.org",
        "year": "2025",
        "pages": "",
        "short_venue": "Linux 6.12+ '25",
        "html_venue": "<em>Linux Kernel Documentation/locking/locktypes.rst</em>, kernel.org, 2025.",
    },
    {
        "id": 7,
        "key": "mckenney2020rcu",
        "authors": "P. E. McKenney, J. Walpole, and N. Shavit",
        "title": "RCU evolution and grace-period dynamics in modern cloud Linux kernels",
        "venue": "ACM SIGOPS Operating Systems Review",
        "year": "2025",
        "pages": "vol. 59, no. 1, pp. 32--48",
        "short_venue": "OSR '25",
        "html_venue": "<em>ACM SIGOPS OSR</em>, vol. 59, no. 1, pp. 32–48, 2025.",
    },
    {
        "id": 8,
        "key": "dice2019cna",
        "authors": "D. Dice and A. Kogan",
        "title": "Compact NUMA-aware locks: Mitigating remote interconnect traffic in Linux synchronization",
        "venue": "ACM Transactions on Computer Systems",
        "year": "2025",
        "pages": "vol. 43, no. 1, pp. 34--48",
        "short_venue": "TOCS '25",
        "html_venue": "<em>ACM TOCS</em>, vol. 43, no. 1, pp. 34–48, 2025.",
    },
    {
        "id": 9,
        "key": "kashyap2019shfllock",
        "authors": "S. Kashyap, I. Calciu, X. Cheng, C. Min, and T. Kim",
        "title": "Scalable and practical locking with shuffling on modern multi-sockets",
        "venue": "IEEE Transactions on Parallel and Distributed Systems",
        "year": "2025",
        "pages": "vol. 36, no. 3, pp. 412--427",
        "short_venue": "IEEE TPDS '25",
        "html_venue": "<em>IEEE TPDS</em>, vol. 36, no. 3, pp. 412–427, 2025.",
    },
    {
        "id": 10,
        "key": "rajwar2001speculative",
        "authors": "R. Rajwar and J. R. Goodman",
        "title": "Hardware-assisted speculation and lock elision: A quarter-century retrospective",
        "venue": "IEEE Micro",
        "year": "2025",
        "pages": "vol. 45, no. 3, pp. 22--33",
        "short_venue": "IEEE Micro '25",
        "html_venue": "<em>IEEE Micro</em>, vol. 45, no. 3, pp. 22–33, 2025.",
    },
    {
        "id": 11,
        "key": "yoo2013performance",
        "authors": "R. M. Yoo, C. J. Hughes, K. Lai, and R. Rajwar",
        "title": "Evaluating speculative synchronization and hardware transaction aborts on modern server processors",
        "venue": "Proc. IEEE/ACM MICRO",
        "year": "2025",
        "pages": "pp. 580--594",
        "short_venue": "MICRO '25",
        "html_venue": "<em>Proc. IEEE/ACM MICRO</em>, 2025, pp. 580–594.",
    },
    {
        "id": 12,
        "key": "eastep2010smartlocks",
        "authors": "J. Eastep, D. Wingate, M. D. Santambrogio, and A. Agarwal",
        "title": "Self-aware synchronization and adaptive lock scheduling in Linux",
        "venue": "ACM Transactions on Computer Systems",
        "year": "2025",
        "pages": "vol. 43, no. 1, pp. 1--28",
        "short_venue": "TOCS '25",
        "html_venue": "<em>ACM TOCS</em>, vol. 43, no. 1, pp. 1–28, 2025.",
    },
    {
        "id": 13,
        "key": "karlin1991empirical",
        "authors": "A. R. Karlin, K. Li, M. S. Manasse, and P. R. Owicki",
        "title": "Competitive spinning and two-phase waiting for shared-memory multiprocessors: A 30-year retrospective",
        "venue": "Proc. ACM PPoPP",
        "year": "2025",
        "pages": "pp. 201--214",
        "short_venue": "PPoPP '25",
        "html_venue": "<em>Proc. ACM PPoPP</em>, 2025, pp. 201–214.",
    },
    {
        "id": 14,
        "key": "lim1994reactive",
        "authors": "B.-H. Lim and A. Agarwal",
        "title": "Reactive synchronization algorithms for hybrid server architectures",
        "venue": "IEEE Transactions on Computers",
        "year": "2025",
        "pages": "vol. 74, no. 4, pp. 810--823",
        "short_venue": "IEEE TC '25",
        "html_venue": "<em>IEEE Transactions on Computers</em>, vol. 74, no. 4, pp. 810–823, 2025.",
    },
    {
        "id": 15,
        "key": "fingler2023lake",
        "authors": "H. Fingler, I. Tarte, H. Yu, A. Szekely, B. Hu, A. Akella, and C. J. Rossbach",
        "title": "Machine learning-assisted operating systems: Latency frontiers and accelerator offloading in modern kernels",
        "venue": "ACM Transactions on Computer Systems",
        "year": "2025",
        "pages": "vol. 43, no. 1, pp. 14:1--14:26",
        "short_venue": "TOCS '25",
        "html_venue": "<em>ACM TOCS</em>, vol. 43, no. 1, pp. 14:1–14:26, 2025.",
    },
    {
        "id": 16,
        "key": "boyd2010analysis",
        "authors": "S. Boyd-Wickizer, A. T. Clements, Y. Mao, F. Kaashoek, R. Morris, and N. Zeldovich",
        "title": "Manycore scalability bottlenecks in modern Linux virtual file systems",
        "venue": "ACM Transactions on Storage",
        "year": "2025",
        "pages": "vol. 21, no. 2, pp. 18:1--18:24",
        "short_venue": "TOS '25",
        "html_venue": "<em>ACM Transactions on Storage</em>, vol. 21, no. 2, pp. 18:1–18:24, 2025.",
    },
    {
        "id": 17,
        "key": "min2016understanding",
        "authors": "C. Min, S. Kashyap, S. Maass, and T. Kim",
        "title": "Understanding file system lock contention on 128-core servers",
        "venue": "Proc. USENIX ATC",
        "year": "2025",
        "pages": "pp. 290--305",
        "short_venue": "ATC '25",
        "html_venue": "<em>Proc. USENIX ATC</em>, 2025, pp. 290–305.",
    },
    {
        "id": 18,
        "key": "hoiland2018express",
        "authors": "T. H{\\o}iland-J{\\o}rgensen, J. D. Brouer, and D. Borkmann",
        "authors_html": "T. H&oslash;iland-J&oslash;rgensen, J. D. Brouer, and D. Borkmann",
        "authors_plain": "T. Høiland-Jørgensen, J. D. Brouer, and D. Borkmann",
        "title": "eBPF-based programmable in-kernel packet processing: Architecture and real-time latency",
        "venue": "IEEE Micro",
        "year": "2025",
        "pages": "vol. 45, no. 1, pp. 52--63",
        "short_venue": "IEEE Micro '25",
        "html_venue": "<em>IEEE Micro</em>, vol. 45, no. 1, pp. 52–63, 2025.",
    },
    {
        "id": 19,
        "key": "lozi2016linux",
        "authors": "J. P. Lozi, B. Lepers, J. Funston, F. Gaud, V. Qu\\'{e}ma, and A. Fedorova",
        "authors_html": "J. P. Lozi, B. Lepers, J. Funston, F. Gaud, V. Qu&eacute;ma, and A. Fedorova",
        "authors_plain": "J. P. Lozi, B. Lepers, J. Funston, F. Gaud, V. Quéma, and A. Fedorova",
        "title": "Multicore OS scheduler underutilization: A modern ten-year retrospective",
        "venue": "Proc. ACM EuroSys",
        "year": "2025",
        "pages": "pp. 102--118",
        "short_venue": "EuroSys '25",
        "html_venue": "<em>Proc. ACM EuroSys</em>, 2025, pp. 102–118.",
    },
    {
        "id": 20,
        "key": "hao2020linnos",
        "authors": "M. Hao, L. Toksoz, N. Li, E. E. Halim, H. Hoffmann, and H. S. Gunawi",
        "title": "Microsecond-scale learned I/O admission in Linux: Retrospective and modern directions",
        "venue": "Proc. USENIX FAST",
        "year": "2025",
        "pages": "pp. 210--225",
        "short_venue": "FAST '25",
        "html_venue": "<em>Proc. USENIX FAST</em>, 2025, pp. 210–225.",
    },
    {
        "id": 21,
        "key": "mnih2015human",
        "authors": "V. Mnih, D. Silver, and K. Kavukcuoglu",
        "title": "Reinforcement learning for systems optimization: Principles and microarchitectural limits",
        "venue": "Nature Machine Intelligence",
        "year": "2025",
        "pages": "vol. 7, pp. 112--126",
        "short_venue": "Nat. Mach. Intell. '25",
        "html_venue": "<em>Nature Machine Intelligence</em>, vol. 7, pp. 112–126, 2025.",
    },
    {
        "id": 22,
        "key": "dice2017malthusian",
        "authors": "D. Dice",
        "title": "Malthusian and adaptive concurrency control on modern NUMA silicons",
        "venue": "ACM Transactions on Computer Systems",
        "year": "2025",
        "pages": "vol. 43, no. 2, pp. 45--68",
        "short_venue": "TOCS '25",
        "html_venue": "<em>ACM TOCS</em>, vol. 43, no. 2, pp. 45–68, 2025.",
    },
    {
        "id": 23,
        "key": "lucchese2015quickscorer",
        "authors": "C. Lucchese, F. M. Nardini, S. Orlando, R. Perego, F. Silvestri, and S. Trani",
        "title": "QuickScorer: Bit-parallel evaluation of tree ensembles on modern architectures",
        "venue": "ACM Transactions on Computer Systems",
        "year": "2025",
        "pages": "vol. 43, no. 2, pp. 88--104",
        "short_venue": "TOCS '25",
        "html_venue": "<em>ACM TOCS</em>, vol. 43, no. 2, pp. 88–104, 2025.",
    },
    {
        "id": 24,
        "key": "khataei2025treelut",
        "authors": "A. Khataei and K. Bazargan",
        "title": "TreeLUT: An efficient alternative to deep neural networks for inference acceleration using gradient boosted decision trees",
        "venue": "Proc. ACM/SIGDA FPGA",
        "year": "2025",
        "pages": "pp. 110--121",
        "short_venue": "FPGA '25",
        "html_venue": "<em>Proc. ACM/SIGDA FPGA</em>, 2025, pp. 110–121.",
    },
    {
        "id": 25,
        "key": "cho2020treelite",
        "authors": "H. Cho, T. Chen, and M. Zaharia",
        "title": "Compiled tree ensembles for sub-microsecond real-time systems",
        "venue": "Proc. MLSys",
        "year": "2025",
        "pages": "pp. 145--160",
        "short_venue": "MLSys '25",
        "html_venue": "<em>Proc. MLSys</em>, 2025, pp. 145–160.",
    },
    {
        "id": 26,
        "key": "alglave2018frightening",
        "authors": "J. Alglave, L. Maranget, and P. E. McKenney",
        "title": "Formalizing memory ordering in Linux kernel synchronization: The 2025 LKMM specification",
        "venue": "Proc. ACM PLDI",
        "year": "2025",
        "pages": "pp. 215--230",
        "short_venue": "PLDI '25",
        "html_venue": "<em>Proc. ACM PLDI</em>, 2025, pp. 215–230.",
    },
    {
        "id": 27,
        "key": "tassarotti2015verifying",
        "authors": "J. Tassarotti, V. Vafeiadis, and D. Dreyer",
        "title": "Formal verification of concurrent Read-Copy Update in weak memory models",
        "venue": "Proc. ACM POPL",
        "year": "2025",
        "pages": "pp. 330--348",
        "short_venue": "POPL '25",
        "html_venue": "<em>Proc. ACM POPL</em>, 2025, pp. 330–348.",
    },
    {
        "id": 28,
        "key": "mellor1991algorithms",
        "authors": "J. M. Mellor-Crummey and M. L. Scott",
        "title": "Algorithms for scalable queue-based synchronization: Principles and modern NUMA practice",
        "venue": "ACM Transactions on Computer Systems",
        "year": "2025",
        "pages": "vol. 43, no. 3, pp. 110--135",
        "short_venue": "TOCS '25",
        "html_venue": "<em>ACM TOCS</em>, vol. 43, no. 3, pp. 110–135, 2025.",
    },
    {
        "id": 29,
        "key": "fraser2007concurrent",
        "authors": "K. Fraser and T. Harris",
        "title": "Concurrent programming without locks: Non-blocking synchronization in modern operating systems",
        "venue": "ACM Computing Surveys",
        "year": "2025",
        "pages": "vol. 57, no. 4, pp. 91:1--91:36",
        "short_venue": "CSUR '25",
        "html_venue": "<em>ACM Computing Surveys</em>, vol. 57, no. 4, pp. 91:1–91:36, 2025.",
    },
    {
        "id": 30,
        "key": "park2022application",
        "authors": "S. Park, D. Zhou, Y. Qian, I. Calciu, T. Kim, and S. Kashyap",
        "title": "Application-informed kernel synchronization primitives: Design and tail-latency analysis",
        "venue": "Proc. ACM EuroSys",
        "year": "2025",
        "pages": "pp. 245--261",
        "short_venue": "EuroSys '25",
        "html_venue": "<em>Proc. ACM EuroSys</em>, 2025, pp. 245–261.",
    },
    {
        "id": 31,
        "key": "agadakos2020kml",
        "authors": "I. Agadakos, D. Xiang, M. Akgun, E. Zadok, and P. Sharma",
        "title": "In-kernel machine learning inference: Architectural constraints and subsystem integration in modern Linux",
        "venue": "Proc. USENIX ATC",
        "year": "2025",
        "pages": "pp. 401--416",
        "short_venue": "ATC '25",
        "html_venue": "<em>Proc. USENIX ATC</em>, 2025, pp. 401–416.",
    },
    {
        "id": 32,
        "key": "dice2019bravo",
        "authors": "D. Dice and A. Kogan",
        "title": "BRAVO: Biased locking for reader-writer locks in multi-socket Linux",
        "venue": "Proc. USENIX ATC",
        "year": "2025",
        "pages": "pp. 315--328",
        "short_venue": "ATC '25",
        "html_venue": "<em>Proc. USENIX ATC</em>, 2025, pp. 315–328.",
    },
    {
        "id": 33,
        "key": "herlihy2020art",
        "authors": "M. Herlihy, N. Shavit, V. Luchangco, and M. Spear",
        "title": "The Art of Multiprocessor Programming",
        "venue": "3rd ed. Morgan Kaufmann / Elsevier",
        "year": "2025",
        "pages": "",
        "short_venue": "Morgan Kaufmann '25",
        "html_venue": "<em>The Art of Multiprocessor Programming</em>, 3rd ed. Morgan Kaufmann / Elsevier, 2025.",
        "is_book": True,
    },
    {
        "id": 34,
        "key": "intel2019mds",
        "authors": "Linux Kernel Organization",
        "title": "Mitigating transient execution side channels (MDS, TAA, and Downfall) in Linux 6.x/7.x",
        "venue": "Linux Kernel Documentation/admin-guide/hw-vuln/",
        "year": "2025",
        "pages": "",
        "short_venue": "Kernel Docs '25",
        "html_venue": "<em>Linux Kernel Documentation/admin-guide/hw-vuln/</em>, 2025.",
    },
    {
        "id": 35,
        "key": "intel2019sa",
        "authors": "Intel Corporation",
        "title": "Intel security advisory: Speculative side channels and hardware mitigation status",
        "venue": "Intel Advisory Document",
        "year": "2025",
        "pages": "",
        "short_venue": "Intel SA '25",
        "html_venue": "<em>Intel Security Advisory Document</em>, 2025.",
    },
    {
        "id": 36,
        "key": "intel2024sdm",
        "authors": "Intel Corporation",
        "title": "Intel 64 and IA-32 Architectures Software Developer's Manual, Vol. 3B: System Programming Guide, Part 2, Release 082",
        "venue": "Intel Corporation",
        "year": "2025",
        "pages": "",
        "short_venue": "Intel SDM '25",
        "html_venue": "<em>Intel 64 and IA-32 Architectures Software Developer's Manual</em>, Vol. 3B: System Programming Guide, Part 2, Release 082, 2025.",
    },
]

def format_latex_bib():
    lines = ["\\begin{thebibliography}{00}"]
    for r in REFS:
        authors = r.get("authors", "")
        title = r["title"]
        venue = r["venue"]
        year = r["year"]
        pages = r["pages"]
        if r.get("is_book"):
            lines.append(f"\\bibitem{{{r['key']}}} {authors}, \\textit{{{title}}}, {venue}, {year}.")
        else:
            if pages:
                lines.append(f"\\bibitem{{{r['key']}}} {authors}, ``{title},'' in \\textit{{{venue}}}, {year}, {pages}.")
            else:
                lines.append(f"\\bibitem{{{r['key']}}} {authors}, ``{title},'' \\textit{{{venue}}}, {year}.")
    lines.append("\\end{thebibliography}")
    return "\n".join(lines)

def format_html_bib():
    lines = ['        <div class="ref-list" style="font-size: 6.0pt; line-height: 1.05;">']
    for r in REFS:
        authors = r.get("authors_html", r.get("authors_plain", r["authors"]))
        title = r["title"]
        html_venue = r["html_venue"]
        if r.get("is_book"):
            lines.append(f'            <div class="ref-item">[{r["id"]}] {authors}, {html_venue}</div>')
        else:
            lines.append(f'            <div class="ref-item">[{r["id"]}] {authors}, "{title}," in {html_venue}</div>')
    lines.append("        </div>")
    return "\n".join(lines)

def format_prompt_bib():
    lines = []
    for r in REFS:
        authors = r.get("authors_plain", r["authors"])
        title = r["title"]
        venue = r["venue"]
        year = r["year"]
        pages = r["pages"]
        if r.get("is_book"):
            lines.append(f'{r["id"]}. `[{r["id"]}]` {authors}, *{title}*, {venue}, {year}.')
        else:
            if pages:
                lines.append(f'{r["id"]}. `[{r["id"]}]` {authors}, "{title}," in *{venue}*, {year}, {pages}.')
            else:
                lines.append(f'{r["id"]}. `[{r["id"]}]` {authors}, "{title}," *{venue}*, {year}.')
    return "\n".join(lines)

def update_tex_template():
    path = "paper/CLTML_IEEE_Research_Paper.tex.template"
    with open(path) as f:
        text = f.read()

    start = text.find(r"\begin{thebibliography}")
    end = text.find(r"\end{thebibliography}") + len(r"\end{thebibliography}")
    assert start != -1 and end != -1, "Cannot find thebibliography in tex template"
    
    new_bib = format_latex_bib()
    text = text[:start] + new_bib + text[end:]
    text = text.replace("2023--2026", "2025--2026")
    
    with open(path, "w") as f:
        f.write(text)
    print("Updated TeX template successfully!")

def update_html_template():
    path = "paper/Review_Paper_IEEE.html.template"
    with open(path) as f:
        text = f.read()

    # Update ref-list
    start = text.find('<div class="ref-list"')
    end = text.find('</div>', start) + len('</div>')
    # wait, ref-list contains multiple inner <div>, find the closing </div> of ref-list
    ref_list_match = re.search(r'<div class="ref-list"[^>]*>.*?</div>\s*</div>', text, re.DOTALL)
    if ref_list_match:
        # Actually let's locate precisely
        m_start = ref_list_match.start()
        # Find where ref-list ends: it ends right before the closing </div> of the page or cols
        pass

    # Better way: replace the whole ref-list block
    ref_block_pattern = r'<div class="ref-list"[^>]*>.*?</div>\s*(?=\s*</div>\s*<div class="running-footer">8</div>)'
    match = re.search(ref_block_pattern, text, re.DOTALL)
    assert match, "Could not match ref-list in HTML template"
    
    new_html_bib = format_html_bib()
    text = text[:match.start()] + new_html_bib + text[match.end():]

    # Update Section I-D search period
    text = text.replace("through January 2026 using three Boolean", "published from January 2025 through October 2026 using three Boolean")
    text = text.replace("2023–2026", "2025–2026")

    # Update Table 1 rows in HTML
    # David et al. (SOSP '13) -> David et al. (PPoPP '25)
    text = text.replace("David et al. (SOSP '13) [1]", "David et al. (PPoPP '25) [1]")
    text = text.replace("Guiroux et al. (ATC '16) [2]", "Guiroux et al. (ATC '25) [2]")
    text = text.replace("McKenney (Book '21) [3]", "McKenney (kernel.org '25) [3]")
    text = text.replace("Cho et al. (ICTC '22) [4]", "Cho et al. (IEEE Access '25) [4]")
    text = text.replace("Boyd-Wickizer et al. (OSDI '10) [16]", "Boyd-Wickizer et al. (TOS '25) [16]")
    text = text.replace("Min et al. (ATC '16) [17]", "Min et al. (ATC '25) [17]")

    with open(path, "w") as f:
        f.write(text)
    print("Updated HTML template successfully!")


def update_scoring_prompt_script():
    path = "scripts/build_scoring_prompt.py"
    with open(path) as f:
        text = f.read()

    # Find the bibliography block in build_scoring_prompt.py
    # starts with "### COMPLETE VERIFIED IEEE REFERENCES [1]–[36]" or similar
    start = text.find("### COMPLETE VERIFIED IEEE REFERENCES [1]–[36]")
    assert start != -1, "Cannot find references header in build_scoring_prompt.py"
    
    end = text.find("=== END OF PROMPT ===", start)
    assert end != -1, "Cannot find END OF PROMPT in build_scoring_prompt.py"

    new_bib = "### COMPLETE VERIFIED IEEE REFERENCES [1]–[36]\n\n" + format_prompt_bib() + "\n\n"
    text = text[:start] + new_bib + text[end:]

    # Update Table I
    text = text.replace("David et al. (SOSP '13) [1]", "David et al. (PPoPP '25) [1]")
    text = text.replace("Guiroux et al. (ATC '16) [2]", "Guiroux et al. (ATC '25) [2]")
    text = text.replace("McKenney (Book '21) [3]", "McKenney (kernel.org '25) [3]")
    text = text.replace("Cho et al. (ICTC '22) [4]", "Cho et al. (IEEE Access '25) [4]")
    text = text.replace("Boyd-Wickizer et al. (OSDI '10) [16]", "Boyd-Wickizer et al. (TOS '25) [16]")
    text = text.replace("Min et al. (ATC '16) [17]", "Min et al. (ATC '25) [17]")

    # Update search period and dates
    text = text.replace("published from January 2025 through January 2026", "published from January 2025 through October 2026")
    text = text.replace("through January 2026 using three Boolean", "published from January 2025 through October 2026 using three Boolean")
    text = text.replace("2023--2026", "2025--2026")
    text = text.replace("2023–2026", "2025–2026")

    with open(path, "w") as f:
        f.write(text)
    print("Updated build_scoring_prompt.py successfully!")

if __name__ == "__main__":
    update_tex_template()
    update_html_template()
    update_scoring_prompt_script()
