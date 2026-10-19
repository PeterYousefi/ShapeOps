# Digital Engineering Lab

The current product direction is a light, calm CAD and ML engineering workspace. It supersedes the original dark dashboard direction. Inference Studio leads the visual system: an open mint-white engineering grid, large selectable B-rep geometry, compact input controls, and a contextual face inspector.

## Tokens

| Role | Color |
|---|---|
| App | #F4F8F6 |
| Panel | #FFFFFF |
| Secondary panel | #EAF1EE |
| Border | #D8E3DF |
| Primary text | #1F2A2E |
| Secondary text | #607076 |
| Primary action | #2F6FED |
| Secondary accent | #6DB8A7 |
| Supporting accent | #A7D7CC |
| Warning/selection | #E7A85F |

DM Sans supports interface reading; IBM Plex Mono distinguishes measurements, trace identifiers and section numbering. Blue is reserved for actions and active navigation. Mint communicates geometry and quiet operational status. Amber identifies selected surfaces and warnings. Never rely on color alone: classes, status badges, confidence values and comparison labels remain textual.

## Composition

Compact persistent navigation; full mobile drawer; bounded content with generous whitespace. Studio geometry dominates the main column. The inspector is separate from the rendering surface. A linked face explorer retains keyboard-accessible selection. Registry versions are selectable release nodes with an artifact inspector, evaluation comparison, lineage and explicit empty promotion history. Overview uses a shared measurement strip and asymmetric workspace rather than independent KPI cards. Operational records use a chronological visual spine.

`src/lab.css` owns the new semantic tokens and page composition over the existing functional component rules. It is loaded after the legacy stylesheet. Further extraction of legacy component rules should preserve tested behavior and avoid another theme override layer.

## Data integrity

All operational data remains API-backed. Samples are labeled. Registry stage is not presented as a production deployment. Missing promotion history remains empty. Procedural evaluation and drift limitations stay visible. No fabricated release dates, trends, confidence or service traffic.
