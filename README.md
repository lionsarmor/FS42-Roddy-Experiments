# FS42 Roddy Experiments

Archive of Roddy's earlier FieldStation42 forks, playback experiments, and tools. For the original project and ongoing upstream development, see [Shane Mason's FieldStation42](https://github.com/shane-mason/FieldStation42).

## Archived repositories

| Original repository | Archived branch | What it contains |
| --- | --- | --- |
| `lionsarmor/FieldStation42` | [FieldStation42/main](https://github.com/lionsarmor/FS42-Roddy-Experiments/tree/FieldStation42/main) | Earlier fork, with separate branches for cloud playback, cable streaming, page streaming, and development. |
| `lionsarmor/FS42_Tools` | [FS42_Tools/main](https://github.com/lionsarmor/FS42-Roddy-Experiments/tree/FS42_Tools/main) | Custom tools for FieldStation42. |
| `lionsarmor/fs42-tsar-tools` | [fs42-tsar-tools/main](https://github.com/lionsarmor/FS42-Roddy-Experiments/tree/fs42-tsar-tools/main) | Earlier TSAR tools for FieldStation42. |

Each archived branch or tag uses its original repository name as a prefix. The preserved commits include their original attribution and license files.

The RODDY Classic TV integration starts from a fresh upstream fork. Its planned Pi-to-Tang path retains FS42's library scanning, scheduling, channel lineup, and program metadata. The Pi decodes only the selected media and sends it to the FPGA, which owns the TV effects, OSD, and display output.
