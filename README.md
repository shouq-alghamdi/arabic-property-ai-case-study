# Al-Ghunaim Holdings — Arabic Property AI Platform

*Engineering case study*

A production AI platform that replaced a fully manual property management
operation: tenancy, maintenance, and contract management for **Al-Ghunaim Holdings**,
a Saudi property holding group, with an Arabic-language assistant over the organisation's own
records.

**This repository contains the case study and one extracted utility.** It does
not contain the platform's source code or any client data — the system is the
client's property. What is here is the engineering reasoning, and the
Arabic-Indic numeral module rebuilt standalone because the problem it solves is
general and badly under-served.

---

## The situation

Al-Ghunaim Holdings is a family-owned group running a portfolio of residential and commercial
units entirely on paper and WhatsApp. No technical staff. Low prior trust in
software vendors, earned from previous attempts.

The brief was a management system. The actual problem was that every
constraint pointed away from the obvious build:

- **The users do not read English, and do not type Modern Standard Arabic.**
  They ask questions the way they speak.
- **The source documents are official Arabic tenancy contracts** — Arabic-Indic
  numerals, right-to-left, inconsistent scans.
- **The client's trust was the scarce resource**, not compute. A confident
  wrong answer about a tenancy would have ended the project.
- **Nobody on the client side could evaluate the system.** Correctness had to
  be demonstrable, not asserted.

Built end to end by a team of two. The system was delivered and sold.

---

## What was built

| Capability | Why it mattered |
|---|---|
| Arabic dialect retrieval assistant | Staff query tenancy, maintenance, and contract records conversationally, in the dialect they actually speak |
| Contract scanning and extraction | Official contracts parsed into structured records rather than re-keyed by hand |
| Role-based access control | A maintenance contractor and the CEO do not see the same portfolio |
| Executive dashboard | Portfolio state at a glance, for a reader who had never used a dashboard |
| Audit trail | Every consequential action, and every record the assistant retrieved to produce an answer |
| WhatsApp notifications | Met users on the channel they already lived on, instead of asking them to move |

**Stack:** Claude API · Supabase · Progressive Web App

---

## Three engineering problems worth writing down

### 1. Arabic-Indic numerals broke the contract pipeline end to end

Official Saudi tenancy contracts write numbers as ٠-٩, not 0-9. Every date
parse, every amount comparison, every numeric field silently failed or threw.

The naive fix — map U+0660-U+0669 to ASCII — is wrong in two ways that only
surface in production:

**Extended Arabic-Indic digits.** Documents that passed through Persian-locale
software carry ۰-۹ (U+06F0-U+06F9), visually near-identical to the Arabic set.
A map covering only the first range leaves these untouched, so a contract
parses fine in testing and fails on one tenant's file.

**Directional formatting marks.** PDF extraction and Arabic text editors inject
zero-width directional isolates around numbers in mixed-direction text. They
are invisible to inspection. Left in place, they split a single number token in
two — `١٢‏٣٤` extracts as two numbers, not one, and the contract value is
wrong rather than missing.

The module is here, standalone and tested:
[`src/arabic_numerals.py`](src/arabic_numerals.py) · 35 tests covering both
digit families, separators, directional contamination, and realistic contract
lines.

```python
>>> from src.arabic_numerals import extract_numbers, to_decimal
>>> extract_numbers("الإيجار ٤٥٬٠٠٠ ريال سنوياً")
['45000']
>>> to_decimal("لا يوجد رقم")
ValueError: no parseable number in 'لا يوجد رقم'
```

That last line is deliberate. The function raises rather than returning zero,
because a silent zero in a contract value is the failure mode this whole module
exists to prevent.

### 2. The assistant had to refuse

A retrieval assistant that answers every question is not useful in this
setting — it is a liability. If the records do not support an answer, inferring
one plausibly is worse than saying nothing, because the user cannot tell the
difference and the client's trust does not survive being wrong once.

So refusal became a tested behaviour rather than a hoped-for one: a 200-case
acceptance suite covering retrieval grounding and declining-to-answer, run per
release, with results recorded.

### 3. Adoption was the hard problem

The client had no technical staff and a well-earned scepticism of software
vendors. Nothing about the system's correctness mattered if it was not used.

What this changed: notifications went to WhatsApp instead of email, because
that was where the work already happened. The dashboard was built for someone
who had never read a dashboard. The assistant answers in dialect. None of this
is technically interesting, and all of it determined whether the project
succeeded.

---

## What I would do differently

**Governance was retrofitted, not designed in.** The system has a strong audit
trail and a real evaluation suite, but no AI policy, no impact assessment, and
no documented cross-border transfer position for prompts reaching a model API
outside the Kingdom. I only found the shape of those gaps when I built a tool
to look for them — and the result scores 38%.

That assessment is published, in full, with the gaps named:
**[ai-compliance-mapper](https://github.com/shouq-alghamdi/ai-compliance-mapper)**

Publishing a failing grade on my own production system is a deliberate choice.
An engineer who cannot name the weaknesses in their own work has not finished
looking.

---

## Running the utility

```bash
pip install pytest
python -m pytest tests/ -q
```

Python 3.10+. No dependencies beyond the standard library.

## Scope and licence

The case study describes work delivered for Al-Ghunaim Holdings and is
published with the client named. No portfolio figures, tenant or contract
records, internal documents, or platform source code appear here — only the
engineering reasoning. The Arabic-Indic numeral module is original
standalone work, published under the MIT licence — see [LICENSE](LICENSE).

---

<div dir="rtl">

## بالعربية

**دراسة حالة هندسية** لمنصة إدارة عقارية إنتاجية بُنيت لمجموعة **الغنيم القابضة**
السعودية، التي كانت تدير محفظتها ورقياً بالكامل، مع مساعد عربي يعمل على سجلات المنشأة نفسها.

**هذا المستودع لا يحتوي كود المنصة ولا أي بيانات للعميل** — النظام ملك
العميل. ما هنا هو المنطق الهندسي، إضافة إلى وحدة معالجة الأرقام العربية
الهندية، أُعيد بناؤها مستقلة لأن المشكلة التي تحلّها عامة ومهمَلة.

**ثلاث مشكلات هندسية تستحق التوثيق:**

١. **الأرقام العربية الهندية (٠-٩)** كسرت خط معالجة العقود بالكامل. والحل
الساذج خاطئ من وجهين لا يظهران إلا في الإنتاج: الأرقام الفارسية (۰-۹)
المشابهة بصرياً، وعلامات الاتجاه عديمة العرض التي تحقنها برامج استخراج
النصوص فتشطر الرقم الواحد إلى رقمين.

٢. **المساعد كان لا بد أن يرفض.** مساعد يجيب عن كل سؤال ليس مفيداً هنا، بل
خطر. فصار الرفض سلوكاً مُختبَراً عبر ٢٠٠ حالة اختبار قبول، لا سلوكاً
مأمولاً.

٣. **التبنّي كان المشكلة الصعبة**، لا الاستدلال. الإشعارات ذهبت إلى واتساب
لأن العمل كان هناك أصلاً، والمساعد يجيب باللهجة.

**ما كنت سأفعله بشكل مختلف:** الحوكمة أُضيفت لاحقاً ولم تُصمَّم من البداية.
بنيتُ أداة للبحث عن الفجوات ثم وجّهتها إلى نظامي هذا، فكانت النتيجة ٣٨٪.
ونشرتُ التقييم كاملاً بفجواته.

</div>
