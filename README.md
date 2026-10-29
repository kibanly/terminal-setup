# terminal-setup

Mi terminal, lista en minutos en cualquier máquina: **zsh** con prompt, autocompletado y atajos, y **tmux** con todo integrado: barra con pestañas y botones, menús con el ratón, una guía de atajos con buscador y un **monitor del sistema** (procesos, puertos, paquetes, contenedores Docker y sus logs).

Funciona en **Ubuntu 26.04**, **Ubuntu 24.04**, **WSL** (Ubuntu dentro de Windows) y **macOS**.

---

## Índice

1. [Qué incluye](#qué-incluye)
2. [Instalación](#instalación)
   - [Ubuntu 26.04 / 24.04](#ubuntu-2604--2404)
   - [WSL (Windows)](#wsl-windows)
   - [macOS](#macos)
3. [Qué hace el instalador](#qué-hace-el-instalador)
4. [Primeros pasos](#primeros-pasos)
5. [Cambiar cosas](#cambiar-cosas)
6. [Actualizar](#actualizar)
7. [Desinstalar](#desinstalar)
8. [Estructura del repo](#estructura-del-repo)
9. [Problemas frecuentes](#problemas-frecuentes)

---

## Qué incluye

**zsh**
- Prompt [starship](https://starship.rs) en dos líneas: usuario, carpeta, rama y estado de git, duración del último comando, hora.
- Sugerencias mientras escribes (`zsh-autosuggestions`) y colores de sintaxis (`zsh-syntax-highlighting`).
- Autocompletado con vista previa ([fzf-tab](https://github.com/Aloxaf/fzf-tab)), `Ctrl+R` para buscar en el historial, `Ctrl+T` para buscar ficheros.
- `ls` con iconos y colores ([eza](https://github.com/eza-community/eza)), `bat` en lugar de `cat`, `micro` como editor.
- Funciones propias:

  | Comando | Qué hace |
  |---|---|
  | `update` | actualiza todo: apt, snap, Homebrew, los plugins de zsh y de tmux |
  | `clean` | limpia cachés y restos de apt, snap, Homebrew, journal y Docker |
  | `installed-packages` | los paquetes que instalaste **tú** (apt, snap, brew) y por qué (notas) |
  | `ports` / `killport <puerto>` | qué escucha en cada puerto / liberarlo (pregunta antes) |
  | `dps` / `dsh` | contenedores Docker de un vistazo / entrar en uno |
  | `fkill` | buscar procesos con fzf y pararlos |
  | `terminal` | gestor de sesiones de tmux (`terminal help`) |

**tmux** (prefijo `Ctrl+a`)
- Barra arriba con las pestañas como botones, CPU y RAM, botones de **menú** y **guía**, y la hora. Se adapta al ancho de la ventana.
- Todo se puede hacer con el ratón: clic en pestañas, clic derecho en paneles, pestañas y sesiones para abrir su menú, rueda para desplazarte.
- `Ctrl+a ?`: **guía** de todos los atajos, con buscador. `Ctrl+a Space`: **menú rápido**.
- **Selector de sesiones** con vista previa (`Ctrl+a s`), descripciones de sesión y árbol de sesiones.
- Las sesiones **sobreviven a un reinicio**: se guardan solas cada 5 minutos ([tmux-resurrect](https://github.com/tmux-plugins/tmux-resurrect) + [continuum](https://github.com/tmux-plugins/tmux-continuum)).
- Antes de cerrar algo que no se puede recuperar (una sesión, una pestaña, un panel con un programa en marcha, el historial), **pregunta**.

**El monitor del sistema** (sesión `system`, se abre sola en cada terminal nueva)

| Pestaña | Contenido |
|---|---|
| 1 · info | resumen del equipo (fastfetch), recursos (CPU, RAM, GPU, discos, red, ping) y btop |
| 2 · monitor | procesos y puertos: ordenar, filtrar, parar (pregunta antes), saltar de uno a otro |
| 3 · packages | tus paquetes (apt, snap, brew) con notas, actualizaciones, buscador e información de cada uno |
| 4 · docker | contenedores, detalle (Dockerfile, compose, configuración final), logs en vivo con buscador |

Cada panel tiene su botón de **zoom**, su menú con clic derecho y se adapta a cualquier tamaño de ventana.

---

## Instalación

Lo único que necesitas antes es **git**. El instalador hace el resto: te enseña lo que va a hacer y pregunta antes de empezar.

```bash
git clone https://github.com/<tu-usuario>/terminal-setup.git ~/workspace/terminal-setup
cd ~/workspace/terminal-setup
./install.sh
```

> El repo puede estar en cualquier carpeta. Si después lo mueves, vuelve a ejecutar `./install.sh` para que los enlaces apunten al sitio nuevo.

Al terminar, **abre una terminal nueva**.

### Ubuntu 26.04 / 24.04

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/<tu-usuario>/terminal-setup.git ~/workspace/terminal-setup
cd ~/workspace/terminal-setup && ./install.sh
```

- Te pedirá tu contraseña (`sudo`) para instalar paquetes.
- **Ubuntu 24.04** trae versiones antiguas de algunas herramientas. El instalador lo detecta y, solo en ese caso:
  - **compila tmux 3.6** (24.04 trae la 3.4, y la configuración necesita la 3.6). Tarda un minuto y se instala en `/usr/local`.
  - instala **fzf**, **fastfetch** y **starship** desde sus versiones oficiales, porque las de 24.04 son antiguas o no existen.
- **Fuente**: si tienes escritorio, la instala en `~/.local/share/fonts`. Después, en la configuración de tu terminal (GNOME Terminal, Konsole, etc.), elige **JetBrainsMono Nerd Font**.
- Por SSH en un servidor: la fuente va en el ordenador **desde el que te conectas**, no en el servidor.

### WSL (Windows)

1. **Instala WSL con Ubuntu** (en PowerShell como administrador) y reinicia si te lo pide:
   ```powershell
   wsl --install -d Ubuntu-24.04
   ```
   (o `Ubuntu-26.04` si ya está disponible: `wsl --list --online` las muestra).
2. **Instala [Windows Terminal](https://aka.ms/terminal)** si no lo tienes (viene con Windows 11).
3. **Dentro de Ubuntu**, igual que en Ubuntu:
   ```bash
   sudo apt update && sudo apt install -y git
   git clone https://github.com/<tu-usuario>/terminal-setup.git ~/workspace/terminal-setup
   cd ~/workspace/terminal-setup && ./install.sh
   ```
4. **La fuente y el perfil se configuran en Windows**, no en Linux: [windows/windows-terminal.md](windows/windows-terminal.md). En resumen, en PowerShell:
   ```powershell
   winget install --id DEVCOM.JetBrainsMonoNerdFont
   ```
   y en Windows Terminal › Configuración › tu perfil de Ubuntu › Apariencia › Tipo de fuente: **JetBrainsMono Nerd Font**.

En WSL, «abrir en el navegador» y `open` usan el navegador y el Explorador **de Windows**.

### macOS

> **Estado**: el instalador y el monitor están adaptados a macOS (procesos con `ps`, puertos con `lsof`, memoria con `vm_stat`, red con `netstat`…) y comprobados con salidas reales de macOS, bash 3.2 y Python 3.9, pero **aún no se han probado en un Mac de verdad**. Si algo falla, `bash install/doctor.sh` es el primer paso.

1. **Herramientas de línea de comandos de Apple** (traen git):
   ```bash
   xcode-select --install
   ```
2. **Clona e instala**:
   ```bash
   git clone https://github.com/<tu-usuario>/terminal-setup.git ~/workspace/terminal-setup
   cd ~/workspace/terminal-setup && ./install.sh
   ```
   Si no tienes [Homebrew](https://brew.sh), el instalador lo instala primero (te pedirá la contraseña). Después instala todo con `brew bundle` (lista en [`install/Brewfile`](install/Brewfile)), **fuente incluida**.
3. **Terminal**: recomiendo [iTerm2](https://iterm2.com), [Ghostty](https://ghostty.org) o [WezTerm](https://wezfurlong.org/wezterm/), que muestran bien los colores y los iconos. En sus ajustes:
   - Fuente: **JetBrainsMono Nerd Font**.
   - **Option como Meta / Alt** (iTerm2: Settings › Profiles › Keys › *Left Option key: Esc+*). Algunos atajos de tmux usan `Alt` (por ejemplo, `Ctrl+a Alt+c`).

---

## Qué hace el instalador

`./install.sh` primero **enseña el plan** (qué falta y qué va a hacer) y pregunta. Luego:

1. **Paquetes**: instala solo los que faltan (apt en Ubuntu/WSL, Homebrew en macOS), con la versión mínima que necesita la configuración (tmux ≥ 3.6, fzf ≥ 0.48…). Versiones en [`install/versions.sh`](install/versions.sh).
2. **Fuente**: JetBrainsMono Nerd Font, donde corresponda (ver arriba).
3. **Enlaces**: tu `~/.zshrc`, `~/.tmux.conf`, `~/.tmux`, etc. pasan a ser **enlaces a los ficheros del repo**. Lo que hubiera antes se guarda en `~/.terminal-setup-backup/<fecha>/`, y `./uninstall.sh` lo devuelve. Si ya tenías `~/.tmux`, tus logs, plugins y descripciones de sesión se conservan.
4. **Plugins** de tmux y zsh, en las versiones probadas ([`install/plugins.lock`](install/plugins.lock)).
5. **zsh como shell** de inicio (pregunta antes; en macOS ya lo es).
6. **Comprobación**: [`install/doctor.sh`](install/doctor.sh) revisa versiones, enlaces, plugins y fuente.

Se puede ejecutar **todas las veces que quieras**: solo hace lo que falta.

| Opción | Qué hace |
|---|---|
| `./install.sh --dry-run` | enseña lo que haría, sin cambiar nada |
| `./install.sh --yes` | sin preguntas (por ejemplo, para scripts) |
| `./install.sh --links-only` | solo los enlaces: ni paquetes, ni fuente, ni plugins |
| `bash install/doctor.sh` | comprobar la instalación en cualquier momento |

**Qué se instala**

| | Ubuntu 26.04 / WSL | Ubuntu 24.04 | macOS |
|---|---|---|---|
| zsh, git, python3, jq, eza, bat, micro, btop, entr, ansifilter, git-delta, zsh-autosuggestions, zsh-syntax-highlighting | apt | apt | Homebrew (zsh y python3 ya vienen) |
| tmux ≥ 3.6 | apt | compilado | Homebrew |
| fzf ≥ 0.48 | apt | binario oficial (`~/.local/bin`) | Homebrew |
| fastfetch | apt | `.deb` oficial | Homebrew |
| starship | apt | instalador oficial (`~/.local/bin`) | Homebrew |
| coreutils, flock | ya vienen | ya vienen | Homebrew |
| JetBrainsMono Nerd Font | `~/.local/share/fonts` (en WSL: en Windows) | igual | Homebrew |
| plugins (tpm, resurrect, continuum, extrakto, fzf-url, logging, cowboy, autoreload, fzf-tab) | git | git | git |

**Opcionales** (si están, se usan; si no, no pasa nada): **Docker** (pestaña docker), **gh** (GitHub), **snap** y **Homebrew** en Linux (aparecen en la pestaña packages), **nvidia-smi** (GPU en Resources).

---

## Primeros pasos

Abre una terminal nueva: tmux arranca solo y te lleva al **monitor del sistema**. Desde ahí:

| Quiero… | Cómo |
|---|---|
| ver todos los atajos | `Ctrl+a ?` (o el botón **󰋖 guide** arriba a la derecha) |
| el menú con lo más usado | `Ctrl+a Space` (o **󰍜 menu**, o clic derecho en la barra) |
| abrir / cambiar de sesión | `Ctrl+a s` · en la terminal: `terminal` |
| una sesión nueva para un proyecto | `Ctrl+a s`, escribe el nombre, Enter, elige la carpeta |
| pestaña nueva / dividir | `Ctrl+a c` · `Ctrl+a v` (al lado) · `Ctrl+a -` (debajo) |
| volver al monitor | `Ctrl+a M` (o clic en CPU / RAM de la barra) |
| una terminal sin tmux | `Ctrl+a d`: sales de tmux al shell normal y tmux sigue funcionando (vuelves con `terminal`). Para que no arranque nunca: `export TERMINAL_NO_AUTOSTART=1` en `~/.zshrc.local` |

> **`Ctrl+a`** es el prefijo de tmux: pulsa `Ctrl+a`, suelta, y luego la tecla. Mientras está activo, la barra se pone roja y muestra «press a key».

---

## Cambiar cosas

Como `~/.zshrc`, `~/.tmux.conf` y `~/.tmux` son **enlaces al repo**, lo que edites ahí **ya está en el repo**: haz `git commit` y llévalo a tus otras máquinas con `git pull`.

- **tmux** recarga la configuración solo al guardar `~/.tmux.conf` (o `Ctrl+a r`).
- **zsh**: abre una terminal nueva o ejecuta `exec zsh`.
- **Solo para esta máquina** (alias propios, rutas, `TERMINAL_NO_AUTOSTART`…): crea `~/.zshrc.local`. Se carga al final y no está en el repo.

| Quiero cambiar… | Fichero |
|---|---|
| alias | `zsh/aliases.zsh` |
| funciones (`update`, `ports`…) | `zsh/functions.zsh` |
| algo solo de Linux / WSL / macOS | `zsh/platform/<linux, wsl, macos>.zsh` |
| el prompt | `config/starship.toml` |
| atajos, colores y barra de tmux | `tmux/tmux.conf` |
| el monitor del sistema | `tmux/system.sh` (pestañas) y los `.py` / `system/*.sh` de cada panel |
| la guía (`Ctrl+a ?`) | `tmux/guide.zsh` |

---

## Actualizar

```bash
cd ~/workspace/terminal-setup
git pull          # lo último del repo
./install.sh      # instala lo que haga falta para esa versión (si no falta nada, no hace nada)
update            # paquetes del sistema y plugins a su última versión
```

---

## Desinstalar

```bash
cd ~/workspace/terminal-setup && ./uninstall.sh
```

Quita los enlaces y **devuelve tus ficheros anteriores** desde la última copia en `~/.terminal-setup-backup/` (o la que le indiques: `./uninstall.sh ~/.terminal-setup-backup/<fecha>`). Los paquetes, la fuente y los plugins **se quedan instalados**, porque otras cosas pueden usarlos.

---

## Estructura del repo

```
terminal-setup/
├── install.sh / uninstall.sh       instalar / deshacer
├── install/
│   ├── lib.sh                      funciones comunes (detectar el sistema, enlaces, copias)
│   ├── versions.sh                 versiones mínimas y las que se descargan
│   ├── apt.sh                      Ubuntu / WSL
│   ├── tmux-build.sh               compila tmux (Ubuntu 24.04)
│   ├── brew.sh · Brewfile          macOS
│   ├── fonts.sh                    JetBrainsMono Nerd Font
│   ├── plugins.sh · plugins.lock   plugins en sus versiones probadas
│   └── doctor.sh                   comprobación
├── zsh/
│   ├── zshrc                       → ~/.zshrc
│   ├── aliases.zsh                 → ~/.zsh_aliases
│   ├── functions.zsh               → ~/.zsh_functions
│   └── platform/                   lo propio de linux / wsl / macos
├── tmux/                           → ~/.tmux
│   ├── tmux.conf                   → ~/.tmux.conf
│   ├── terminal.zsh                gestor de sesiones (comando `terminal`, selector)
│   ├── guide.zsh · quick-menu.zsh  guía (Ctrl+a ?) y menú rápido (Ctrl+a Space)
│   ├── system.sh                   construye el monitor (sesión `system`)
│   ├── *.py                        los paneles del monitor
│   └── system/                     scripts del monitor (info, recursos, btop, abrir URLs…)
├── config/
│   ├── starship.toml               → ~/.config/starship.toml
│   ├── btop/btop.conf              → ~/.config/btop/btop.conf
│   └── micro/settings.json         → ~/.config/micro/settings.json
└── windows/windows-terminal.md     WSL: fuente y perfil de Windows Terminal
```

**No van al repo** (son de cada máquina): los plugins descargados, los logs de tmux (`~/.tmux/logs`), las descripciones de sesión (`~/.tmux/descriptions.tsv`), los guardados de sesiones de tmux-resurrect, tus notas de paquetes (`~/.apt-notes.tsv`) y `~/.zshrc.local`.

---

## Problemas frecuentes

**Veo cuadrados `□` o interrogantes en vez de iconos**
La terminal no usa la Nerd Font. Instálala (en WSL: en Windows) y elígela en los ajustes de la terminal: **JetBrainsMono Nerd Font**. `bash install/doctor.sh` te dice si está instalada.

**Al abrir la terminal no arranca tmux**
No arranca dentro de VS Code, JetBrains, por SSH ni si `TERMINAL_NO_AUTOSTART` está puesto. Para abrirlo a mano: `terminal`.

**`tmux: unknown option` o errores al cargar la configuración**
El tmux que se ejecuta es anterior a la 3.6. Comprueba con `tmux -V` y `which tmux`. En Ubuntu 24.04 debería ser `/usr/local/bin/tmux`; si no, vuelve a ejecutar `./install.sh`. Si tenías tmux abierto con la versión vieja, ciérralo del todo: `tmux kill-server`.

**Los atajos con `Alt` no hacen nada (macOS)**
La tecla Option tiene que funcionar como Meta / Alt: ver [macOS](#macos).

**Quiero ver qué falta o qué está mal**
```bash
bash install/doctor.sh
```
