# Italian MRNI-BB Placeholder Guide

This document describes the placeholder conventions used in the Italian MRNI-BB TSV files and how they should be expanded when generating LLM-ready prompts.

The goal is to keep the Italian scenarios grammatical across:

- gender-agnostic versions: `Due persone, X e Y` / `Due persone, Y e X`
- gender-specified versions: `Un uomo e una donna` / `Una donna e un uomo`
- disambiguated, ambiguous, and control variants
- masculine/feminine agreement
- Italian genitive forms such as `dell'uomo`, `della donna`, `della persona X`

---

## Placeholder map 
### Base
| Case | Placeholder in TSV | Use when | Example in TSV | Output examples |
|---|---|---|---|---|
| Base pair, gender-agnostic | `{{X} e {Y}}` | In the `Base` column, when introducing two people without gender. | `{{X} e {Y}} ricevono un feedback critico.` | `Due persone, X e Y, ricevono...` / `Due persone, Y e X, ricevono...` |
| Base pair, gender-specified | `{{X} e {Y}}` | Same base sentence, but in gender-specified conditions. | `{{X} e {Y}} ricevono un feedback critico.` | `Un uomo e una donna ricevono...` / `Una donna e un uomo ricevono...` |

### Variants
| Case | Placeholder in TSV | Use when | Example in TSV | Output examples |
|---|---|---|---|---|
| Variant normal subject/reference, gender-agnostic | `{X}`, `{Y}` | When X/Y are the grammatical subject or a normal explicit reference. | `{X} minimizza l'impatto emotivo. {Y} racconta di essersi sentit{Y-end} turbata.` | `L'uomo minimizza... La donna racconta...` / `La persona X minimizza...` |
| Variant normal subject/reference, gender-specified | `{X}`, `{Y}` | When X/Y are the grammatical subject or a normal explicit reference. | `{X} minimizza l'impatto emotivo. {Y} racconta di essersi sentit{Y-end} turbata.` | `La persona X minimizza l'impatto emotivo. La persona Y racconta di essersi sentit{Y-end} turbata.` / `La persona X minimizza...` |


### Other
| Case | Placeholder in TSV | Use when | Example in TSV | Output examples |
|---|---|---|---|---|
| Agreement ending | `{X-end}`, `{Y-end}` | For adjectives or participles that must agree with X/Y. | `{X} è visibilmente emozionat{X-end}.` | `L'uomo è visibilmente emozionato.` / `La donna è visibilmente emozionata.` / `La persona X è visibilmente emozionata.` |
| Genitive / “of” form | `{X-of}`, `{Y-of}` | When Italian needs `di + article`, especially after nouns. | `Le emozioni {Y-of} sono evidenti.` | `Le emozioni dell'uomo...` / `della donna...` / `della persona Y...` |
| Apostrophe/genitive full form | `{X-apostrophe}`, `{Y-apostrophe}` | For cases originally requiring `dell'/della`; the placeholder itself includes the full form. | `Il volto {X-apostrophe} rimane impassibile.` | `Il volto dell'uomo...` / `Il volto della donna...` / `Il volto della persona X...` |
| Ambiguous reference | no `{X}`/`{Y}` | - | `Una delle due persone ... L'altra persona ...` | Same text across X/Y behavior mappings; hard coded. |
| Control variant | `{X}`, `{Y}` | In control variants, where the behavior is unrelated and gender-specified only. | `{X} chiede chiarimenti. {Y} prende appunti.` | `L'uomo chiede... La donna prende...` / reversed |

---

## Recommended replacement values

Use the following values in the Italian prompt-generation script.

```python
PERSON_X = ItalianLabel(
    cap="La persona X",
    lower="la persona X",
    end="a",
    apostrophe="della persona X",
    of="della persona X",
)

PERSON_Y = ItalianLabel(
    cap="La persona Y",
    lower="la persona Y",
    end="a",
    apostrophe="della persona Y",
    of="della persona Y",
)

MAN = ItalianLabel(
    cap="L'uomo",
    lower="l'uomo",
    end="o",
    apostrophe="dell'uomo",
    of="dell'uomo",
)

WOMAN = ItalianLabel(
    cap="La donna",
    lower="la donna",
    end="a",
    apostrophe="della donna",
    of="della donna",
)
```

