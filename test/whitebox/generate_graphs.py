"""Generates CFG/DFG graphs for all source files in the project

NOTE: You should run this script with python<=3.13 because of poor upstream
maintenance (py2cfg). 
That or download my patched version of py2cfg which has been
(mostly) futureproofed for 3.14:

git clone https://gitlab.com/kamilok04/py-2-cfg-ast-patch.git
cd (wherever that got copied to)
pip install -e .

This should probably not be a part of the CI/CD pipeline!
- it's slow
- it really doesn't need to be run often, prefereably just once
- it produces PNGs, useless for automation
  (there is a text output though, could be worth a look)
"""

import importlib
from pathlib import Path
from py2cfg import CFGBuilder

class GraphGenerator():
    def __init__(self, src_path, out_path):
        self.src_path = src_path
        self.out_path = Path(out_path)
        self.filenames = [
            str(p) for p in Path(self.src_path).rglob("*.[pP][yY]")
            if '__init__' not in p.stem
        ]
        
    def generate_cfgs(self):
        cfg = CFGBuilder()
        for f in self.filenames:
            pf = Path(f)
            graph = cfg.build_from_file(str(pf.parent/pf.stem), f)
          
            graph.build_visual(self.out_path/'cfg'/pf, 'png', show=False)
            print(f'Wrote {str(pf)}.png')

if __name__ == "__main__":
    # You should be running this from the project root
    # (the folder which contains src/ and test/)
    # outputs to test/whitebox/{cfg,dfg,prog}
    if not Path.exists('src') or not Path.exists('test'):
        print('You chose the wrong root path, not proceeding')
        exit(1)
    gg = GraphGenerator('src',str(Path('test/whitebox')))
    gg.generate_cfgs()
