#!/usr/bin/env python3
import argparse
import re
import zipfile
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == '.txt':
        return path.read_text(errors='ignore')
    if suffix == '.docx':
        try:
            import docx
            doc = docx.Document(str(path))
            return '\n'.join(p.text for p in doc.paragraphs)
        except Exception:
            with zipfile.ZipFile(path) as z:
                xml = z.read('word/document.xml').decode('utf-8', errors='ignore')
            text = re.sub(r'<w:tab/>', '\t', xml)
            text = re.sub(r'</w:p>', '\n', text)
            text = re.sub(r'<.*?>', '', text)
            return text
    if suffix == '.pdf':
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            return '\n'.join(page.extract_text() or '' for page in reader.pages)
        except Exception:
            return ''
    return path.read_text(errors='ignore')


def find_money(text):
    vals = []
    patterns = [r'\$\s?([\d,]+(?:\.\d+)?)\s?M', r'([\d,]+(?:\.\d+)?)\s?million', r'\$\s?([\d,]+(?:\.\d+)?)']
    lower = text.lower()
    for p in patterns:
        for m in re.findall(p, lower, flags=re.I):
            try:
                v = float(str(m).replace(',', ''))
                if 'million' in p or 'm' in p.lower():
                    vals.append(v * 1_000_000)
                else:
                    if v >= 1000:
                        vals.append(v)
            except:
                pass
    return vals


def parse_offer(text, name):
    lower = text.lower()
    money = find_money(text)
    base_salary = 0
    startup = 0
    salary_support = 0

    salary_match = re.search(r'(annual salary|annualized compensation|base salary|salary will be)\D{0,40}\$?([\d,]{5,9})', lower)
    if salary_match:
        base_salary = float(salary_match.group(2).replace(',', ''))

    for sentence in re.split(r'[\n\.]', lower):
        if any(k in sentence for k in ['start-up', 'startup', 'research funding', 'programmatic support', 'committed a total']):
            nums = find_money(sentence)
            if nums:
                startup = max(startup, max(nums))
        if 'salary' in sentence and any(k in sentence for k in ['support', 'fringe', 'supplement']):
            nums = find_money(sentence)
            if nums:
                salary_support = max(salary_support, max(nums))

    protected = 0.75
    if '100 research' in lower or '100% research' in lower:
        protected = 1.0
    elif 'first year assignment' in lower and 'teaching' in lower and 'service' in lower:
        protected = 0.9
    elif 'teaching' in lower and 'service' in lower:
        protected = 0.75

    carryover = 1 if ('carry forward' in lower or 'carryover' in lower or 'will not expire' in lower) else 0
    mentor = 1 if 'mentor' in lower else 0
    tenure_clock = 7 if 'seven' in lower or '7-year' in lower else 6

    total_package = startup + salary_support
    return {
        'institution': name,
        'base_salary': base_salary,
        'startup_package': startup,
        'salary_support': salary_support,
        'total_package': total_package,
        'protected_research_effort': protected,
        'carryover_friendly': carryover,
        'formal_mentor': mentor,
        'tenure_clock_years': tenure_clock,
    }


def parse_cv(text):
    lower = text.lower()
    def grab(pattern, default=0):
        m = re.search(pattern, lower, flags=re.I)
        return float(m.group(1).replace(',', '')) if m else default

    profile = {
        'citations': grab(r'citations\D{0,10}([\d,]+)'),
        'h_index': grab(r'h-index\D{0,10}([\d,]+)'),
        'first_author_pubs': grab(r'first author publications\D{0,10}([\d,]+)'),
        'senior_author_pubs': grab(r'senior author publications\D{0,10}([\d,]+)'),
        'total_pubs': grab(r'total publications\D{0,10}([\d,]+)'),
        'has_k99_r00': 1 if ('k99' in lower or 'r00' in lower) else 0,
    }
    return profile


def model_outputs(profile, offers):
    base_success_rate = 0.20
    k99_boost = 0.15 if profile['has_k99_r00'] else 0.0
    profile_boost = min(0.15, 0.03 * (profile['h_index'] / 10) + 0.02 * (profile['first_author_pubs'] / 10) + 0.02 * (profile['total_pubs'] / 20))

    years5 = np.arange(1, 6)
    years10 = np.arange(1, 11)
    annual_r01 = {}
    cumulative_r01 = {}
    high_impact = {}
    annual_phd = {}
    cumulative_phd = {}
    grants10 = {}
    summary = []

    for offer in offers:
        name = offer['institution']
        startup_m = offer['total_package'] / 1_000_000 if offer['total_package'] else offer['startup_package'] / 1_000_000
        salary_support_m = offer['salary_support'] / 1_000_000
        startup_factor = min(max(startup_m / 2.0, 0.4), 1.6)
        protected_factor = offer['protected_research_effort']
        support_factor = min(max(0.8 + salary_support_m / 1.2, 0.8), 1.4)
        carry_factor = 1.05 if offer['carryover_friendly'] else 0.97
        mentor_factor = 1.03 if offer['formal_mentor'] else 1.0

        probs = []
        for y in years5:
            time_factor = 1 - np.exp(-y / 2.0)
            p = (base_success_rate + k99_boost + profile_boost) * startup_factor * protected_factor * support_factor * carry_factor * mentor_factor * time_factor
            probs.append(min(p, 0.65))
        annual_r01[name] = probs
        cumulative_r01[name] = float(1 - np.prod([1 - p for p in probs]))

        base_high_pub_rate = 1.2 + 0.1 * profile['has_k99_r00'] + min(profile['first_author_pubs'] / 20, 0.8)
        annual_hi = []
        total_hi = 0
        for y in years10:
            yr = base_high_pub_rate * protected_factor * startup_factor * (1.03 if y <= 5 else 0.98)
            total_hi += yr
            annual_hi.append(total_hi)
        high_impact[name] = annual_hi

        recruit = 0.8 + 0.3 * startup_factor + 0.25 * protected_factor + 0.1 * carry_factor
        retention = min(0.88, 0.72 + 0.08 * startup_factor + 0.05 * protected_factor)
        grads_ann = np.zeros(10)
        recruits = np.full(10, recruit)
        for yr in range(10):
            g = 0
            for lag in range(4, 8):
                if yr - lag >= 0:
                    g += recruits[yr-lag] * (retention ** (lag-3)) * 0.33
            grads_ann[yr] = g
        annual_phd[name] = grads_ann.tolist()
        cumulative_phd[name] = np.cumsum(grads_ann).tolist()

        other_grants = []
        totalg = 0
        other_base = 0.08 + 0.06 * startup_factor + 0.08 * protected_factor + 0.05 * profile['has_k99_r00']
        for y in years10:
            if y <= 5:
                g = min(0.95, annual_r01[name][min(y-1,4)] + other_base)
            else:
                g = min(0.95, annual_r01[name][4] + other_base + 0.02*(y-5))
            totalg += g
            other_grants.append(totalg)
        grants10[name] = other_grants

        tenure_prob_y7 = min(0.97, 0.15 + cumulative_r01[name]*0.5 + (high_impact[name][6]/25)*0.25 + (cumulative_phd[name][6]/8)*0.1)
        summary.append({
            'institution': name,
            'base_salary': round(offer['base_salary'],0),
            'startup_plus_support_m': round((offer['total_package'] or offer['startup_package'])/1_000_000, 3),
            'protected_effort': round(protected_factor,2),
            'r01_5yr_probability': round(cumulative_r01[name], 3),
            'high_impact_pubs_10yr': round(high_impact[name][-1], 1),
            'phd_graduates_10yr': round(cumulative_phd[name][-1], 1),
            'total_grants_10yr': round(grants10[name][-1], 1),
            'tenure_probability_y7': round(tenure_prob_y7, 3),
        })

    return {
        'annual_r01': pd.DataFrame(annual_r01, index=years5),
        'cumulative_r01': pd.DataFrame({'institution': list(cumulative_r01.keys()), 'probability': list(cumulative_r01.values())}),
        'high_impact': pd.DataFrame(high_impact, index=years10),
        'annual_phd': pd.DataFrame(annual_phd, index=years10),
        'cumulative_phd': pd.DataFrame(cumulative_phd, index=years10),
        'grants10': pd.DataFrame(grants10, index=years10),
        'summary': pd.DataFrame(summary),
    }


def save_plots(outdir: Path, outputs):
    outdir.mkdir(parents=True, exist_ok=True)

    plt.style.use('seaborn-v0_8-whitegrid')
    # Annual R01
    ax = outputs['annual_r01'].plot(kind='bar', figsize=(10,6))
    ax.set_title('Annual R01 Success Probability by Offer')
    ax.set_xlabel('Year on Faculty')
    ax.set_ylabel('Probability')
    plt.tight_layout()
    plt.savefig(outdir/'r01_annual.png', dpi=300)
    plt.close()

    # Cumulative R01
    fig, ax = plt.subplots(figsize=(10,6))
    for col in outputs['annual_r01'].columns:
        surv = np.cumprod([1-p for p in outputs['annual_r01'][col].values])
        ax.plot(outputs['annual_r01'].index, 1-surv, marker='o', linewidth=2, label=col)
    ax.set_title('Cumulative Probability of Securing at Least One R01')
    ax.set_xlabel('Year on Faculty')
    ax.set_ylabel('Probability')
    ax.legend()
    plt.tight_layout()
    plt.savefig(outdir/'r01_cumulative.png', dpi=300)
    plt.close()

    # High-impact pubs
    ax = outputs['high_impact'].plot(figsize=(10,6), linewidth=2)
    ax.set_title('Projected Cumulative High-Impact Publications Over 10 Years')
    ax.set_xlabel('Years as Faculty')
    ax.set_ylabel('Cumulative Publications')
    plt.tight_layout()
    plt.savefig(outdir/'high_impact_pubs.png', dpi=300)
    plt.close()

    # Cumulative PhD
    ax = outputs['cumulative_phd'].plot(figsize=(10,6), marker='o', linewidth=2)
    ax.set_title('Cumulative PhD Students Graduated Over 10 Years')
    ax.set_xlabel('Years as Faculty')
    ax.set_ylabel('Cumulative Graduates')
    plt.tight_layout()
    plt.savefig(outdir/'phd_cumulative.png', dpi=300)
    plt.close()

    # Annual PhD
    ax = outputs['annual_phd'].plot(figsize=(10,6), marker='s', linewidth=2)
    ax.set_title('Annual PhD Students Graduated Over 10 Years')
    ax.set_xlabel('Years as Faculty')
    ax.set_ylabel('Graduates per Year')
    plt.tight_layout()
    plt.savefig(outdir/'phd_annual.png', dpi=300)
    plt.close()

    # Grants
    ax = outputs['grants10'].plot(figsize=(10,6), marker='o', linewidth=2)
    ax.set_title('Projected Cumulative Extramural Grants Over 10 Years')
    ax.set_xlabel('Years as Faculty')
    ax.set_ylabel('Cumulative Grants')
    plt.tight_layout()
    plt.savefig(outdir/'grants_10yr.png', dpi=300)
    plt.close()

    # Summary bar panel
    s = outputs['summary'].set_index('institution')[['r01_5yr_probability','tenure_probability_y7','phd_graduates_10yr','total_grants_10yr']]
    fig, axes = plt.subplots(2,2, figsize=(12,9))
    s['r01_5yr_probability'].plot(kind='bar', ax=axes[0,0], title='R01 by Year 5', color='steelblue')
    s['tenure_probability_y7'].plot(kind='bar', ax=axes[0,1], title='Tenure Probability by Year 7', color='darkorange')
    s['phd_graduates_10yr'].plot(kind='bar', ax=axes[1,0], title='PhD Graduates by Year 10', color='seagreen')
    s['total_grants_10yr'].plot(kind='bar', ax=axes[1,1], title='Total Grants by Year 10', color='purple')
    for ax in axes.flat:
        ax.set_xlabel('')
    plt.tight_layout()
    plt.savefig(outdir/'summary_panel.png', dpi=300)
    plt.close()


def write_report(outdir: Path, profile, offers_df, outputs):
    summary = outputs['summary'].sort_values('r01_5yr_probability', ascending=False)
    top = summary.iloc[0]['institution'] if len(summary) else 'N/A'
    md = []
    md.append('# Offer Letter Probability Report\n')
    md.append('## Candidate profile\n')
    md.append(f"- Citations: {int(profile['citations'])}\n")
    md.append(f"- h-index: {int(profile['h_index'])}\n")
    md.append(f"- First-author publications: {int(profile['first_author_pubs'])}\n")
    md.append(f"- Senior-author publications: {int(profile['senior_author_pubs'])}\n")
    md.append(f"- Total publications: {int(profile['total_pubs'])}\n")
    md.append(f"- K99/R00 detected: {'Yes' if profile['has_k99_r00'] else 'No'}\n")
    md.append('\n## Parsed offers\n')
    md.append(offers_df.to_markdown(index=False))
    md.append('\n\n## Modeled outcomes\n')
    md.append(summary.to_markdown(index=False))
    md.append(f"\n\nTop projected package by modeled R01 success: **{top}**\n")
    md.append('\n## Figures\n')
    figs = ['r01_annual.png','r01_cumulative.png','high_impact_pubs.png','phd_cumulative.png','phd_annual.png','grants_10yr.png','summary_panel.png']
    for f in figs:
        md.append(f"- {f}\n")
    (outdir/'report.md').write_text(''.join(md))


def main():
    ap = argparse.ArgumentParser(description='Generate an academic offer probability report from offer letters + CV.')
    ap.add_argument('--cv', required=True, help='Path to CV file (.docx, .pdf, .txt)')
    ap.add_argument('--offers', nargs='+', required=True, help='One or more offer letter files')
    ap.add_argument('--outdir', default='report_output', help='Output directory')
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    cv_text = extract_text(Path(args.cv))
    profile = parse_cv(cv_text)

    offers = []
    for op in args.offers:
        p = Path(op)
        text = extract_text(p)
        offers.append(parse_offer(text, p.stem))
    offers_df = pd.DataFrame(offers)
    offers_df.to_csv(outdir/'parsed_offers.csv', index=False)
    pd.DataFrame([profile]).to_csv(outdir/'parsed_cv_metrics.csv', index=False)

    outputs = model_outputs(profile, offers)
    for k, df in outputs.items():
        if isinstance(df, pd.DataFrame):
            df.to_csv(outdir/f'{k}.csv', index=True)

    save_plots(outdir, outputs)
    write_report(outdir, profile, offers_df, outputs)
    print(f'Report written to: {outdir.resolve()}')

if __name__ == '__main__':
    main()
