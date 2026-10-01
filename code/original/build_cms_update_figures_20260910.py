"""Plot audited data only; no generated or inferred numerical observations."""
from pathlib import Path
import csv
import json
import shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data/dft_runs'
OLD = DATA / 'final-paper-package/paper-priority-analysis-20260725'
OUT = DATA / 'CMS_updated_20260910'
FIG = OUT / 'figures'
plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':9, 'axes.spines.top':False, 'axes.spines.right':False, 'pdf.fonttype':42, 'svg.fonttype':'none'})


def csvread(p):
    with p.open(encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def save(fig, name):
    fig.savefig(FIG / (name + '.png'), dpi=350, bbox_inches='tight', facecolor='white')
    fig.savefig(FIG / (name + '.pdf'), bbox_inches='tight', facecolor='white')
    fig.savefig(FIG / (name + '.svg'), bbox_inches='tight', facecolor='white')
    plt.close(fig)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    for p in (OLD / 'cms_method_submission_ready_20260829/02_figures').glob('Figure_[123]_*'):
        shutil.copyfile(p, FIG / p.name)
    fig,ax=plt.subplots(figsize=(9.4,4.2))
    ax.set(xlim=(0,10),ylim=(0,4.5));ax.axis('off')
    def box(x,y,w,h,title,detail,color):
        ax.add_patch(Rectangle((x,y),w,h,facecolor='#f5f7f8',edgecolor=color,lw=1.2))
        ax.text(x+w/2,y+h-.22,title,ha='center',va='top',weight='bold',fontsize=9,color=color)
        ax.text(x+w/2,y+h/2-.13,detail,ha='center',va='center',fontsize=8,linespacing=1.5)
    for x,title,detail in [(0.15,'Conditional generation','MatterGen proposals\n65 generated / 64 retained'),(3.55,'MLIP relaxation and gates','MatterSim and deterministic checks\n64 strict model-valid candidates'),(6.95,'Selected DFT validation','Historical fixed-geometry screening\n31 / 32 scheduled single points')]:
        box(x,2.8,2.9,1.35,title,detail,'#197d89')
    for x in [3.05,6.45]:
        ax.annotate('',xy=(x+.5,3.47),xytext=(x,3.47),arrowprops=dict(arrowstyle='->',color='#555555',lw=1.2))
    box(.15,.85,4.35,1.4,'Supplementary common-family DFT','8 selected candidate variable-cell relaxations\nPaired reference and numerical convergence checks\nDense-grid ranking and strict-SCF force diagnostics','#9c4046')
    box(5.2,.85,4.65,1.4,'Traceable scientific evidence','Inputs, final structures, energies, forces and stresses\nExplicit historical / supplementary protocol labels\nScientific outputs retained; restart scratch excluded','#485b65')
    ax.plot([8.4,8.4,2.3],[2.8,2.5,2.5],color='#9c4046',lw=1.2)
    ax.annotate('',xy=(2.3,2.25),xytext=(2.3,2.5),arrowprops=dict(arrowstyle='->',color='#9c4046',lw=1.2))
    ax.annotate('',xy=(5.2,1.4),xytext=(4.5,1.4),arrowprops=dict(arrowstyle='->',color='#555555',lw=1.2))
    ax.text(5,.35,'Bounded feasibility study: no language-model decision layer, prospective superiority test or new-phase claim',ha='center',fontsize=8,color='#444444')
    fig.tight_layout()
    save(fig,'Figure_1_method_architecture')
    pairs = csvread(OLD / 'source_data/same_stoichiometry_ranking_pairs.csv')
    fig, axes = plt.subplots(1, 2, figsize=(9.3, 3.7), gridspec_kw={'width_ratios':[1,1.55]})
    x = np.arange(2)
    axes[0].bar(x-.18, [abs(float(p['model_delta_eV_atom']))*1000 for p in pairs], .36, label='MatterSim', color='#197d89')
    axes[0].bar(x+.18, [abs(float(p['dft_delta_eV_atom']))*1000 for p in pairs], .36, label='Historical DFT', color='#bd5356')
    axes[0].set(xticks=x, xticklabels=['Pd:Rh = 1:3','Pt:Pd = 1:1'], ylabel='Pair energy gap (meV/atom)', title='a  Historical cross-fidelity diagnostic')
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].set_ylim(0, 70)
    labels=['Model checkpoint and conditions','Generation seeds and exact runtime','Historical DFT inputs and potentials','Unified-family candidate relaxations','Representative alloy convergence','Two-pair dense-grid ranking','Dense-grid geometry optimization','Prospective selection baseline']
    vals=[1,0,1,1,1,1,0,0]
    axes[1].scatter(vals, np.arange(len(vals)), c=['#197d89' if v else '#bd5356' for v in vals], s=70)
    axes[1].set(yticks=np.arange(len(vals)), yticklabels=labels, xticks=[0,1], xticklabels=['Not established','Recorded'], xlim=(-.3,1.3), title='b  Evidence after supplementary calculations')
    axes[1].invert_yaxis()
    axes[1].tick_params(axis='y', length=0, labelsize=8)
    fig.tight_layout(w_pad=2.5)
    save(fig,'Figure_4_fidelity_and_provenance')
    rows=csvread(DATA / 'main-queue-analysis-20260909/unified_results.csv')
    vals=[float(r['formation_meV_atom']) for r in rows]
    fig, ax=plt.subplots(figsize=(8.4,4.0))
    y=np.arange(len(rows))
    ax.barh(y,vals,color=['#197d89' if v<0 else '#bd5356' for v in vals])
    ax.set(yticks=y,yticklabels=[r['job'].split('_')[0] for r in rows], xlabel='Formation energy relative to fcc elements (meV/atom)')
    ax.axvline(0,color='#444444',lw=.8)
    ax.invert_yaxis()
    for i,v in enumerate(vals): ax.text(v+(1.7 if v>=0 else -1.7),i,f'{v:+.2f}',va='center',ha='left' if v>=0 else 'right',fontsize=8)
    ax.set_xlim(-45,127)
    fig.tight_layout()
    save(fig,'Figure_5_unified_relaxations')
    rows=csvread(DATA / 'convergence-analysis-20260909/formation_convergence.csv')
    cuts=[r for r in rows if r['group'].startswith('c')]
    dense=json.loads((DATA / 'supplement-final-audit-20260909/audit.json').read_text())['dense_comparison']
    dense=sorted(dense,key=lambda r:int(r['alloy_mesh'].split('x')[0]))
    fig,axes=plt.subplots(1,2,figsize=(9,3.8))
    axes[0].plot([float(r['ecutwfc_Ry']) for r in cuts],[float(r['formation_meV_atom']) for r in cuts], 'o-',color='#197d89')
    axes[0].set(xlabel='Wavefunction cutoff (Ry)',ylabel='Formation energy (meV/atom)',title='a  Cutoff series at fixed alloy geometry')
    axes[0].ticklabel_format(useOffset=False,axis='y')
    axes[1].plot(range(5),[r['formation_meV_atom'] for r in dense],'s-',color='#bd5356')
    axes[1].set(xticks=range(5),xticklabels=[r['alloy_mesh']+'\n'+r['ref_mesh'] for r in dense], ylabel='Formation energy (meV/atom)',xlabel='Alloy mesh / elemental reference mesh',title='b  Paired mesh protocols')
    axes[1].tick_params(axis='x',labelsize=7)
    fig.tight_layout(w_pad=2)
    save(fig,'Figure_6_numerical_convergence')
    gaps=csvread(DATA / 'supplement-final-audit-20260909/pair_gaps.csv')
    force=csvread(DATA / 'final-force-audit-20260910/comparison.csv')
    fig,axes=plt.subplots(1,2,figsize=(9,3.8))
    for i,g in enumerate(gaps):
        axes[0].plot([0,1],[float(g['old_gap_meV_atom']),float(g['new_gap_meV_atom'])],'o-',label=['Pt-Pd pair','Pd-Rh pair'][i],color=['#197d89','#bd5356'][i])
    axes[0].set(xticks=[0,1],xticklabels=['Base protocol','Dense protocol'],ylabel='Higher minus lower energy (meV/atom)',title='a  Same-composition ranking')
    axes[0].legend(frameon=False,fontsize=8)
    x=np.arange(4)
    axes[1].bar(x-.18,[float(r['old_correction_Ry_bohr']) for r in force],.36,label='SCF threshold 1e-8 Ry',color='#aeb7bd')
    axes[1].bar(x+.18,[float(r['correction_Ry_bohr']) for r in force],.36,label='SCF threshold 1e-10 Ry',color='#197d89')
    axes[1].set(xticks=x,xticklabels=['Ternary\n20 atoms','Pd-Rh-06','Pt-Pd-01*','Pd-Rh-14'],yscale='log',ylabel='Total SCF force correction (Ry/Bohr)',title='b  Absolute correction after tighter SCF')
    axes[1].tick_params(axis='x',labelsize=7)
    axes[1].legend(frameon=False,fontsize=7)
    axes[1].set_ylim(1e-5, 3e-3)
    fig.tight_layout(w_pad=2)
    save(fig,'Figure_7_ranking_force_precision')
    print(FIG)


if __name__=='__main__': main()
