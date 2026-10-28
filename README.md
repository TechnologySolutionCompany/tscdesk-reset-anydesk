# TSCDesk — Reset AnyDesk

Utilitário Windows que recupera o AnyDesk travado ou sem conexão em um clique, com painel de status, log de execução e reinstalação limpa quando necessário.

<p>
  <img alt="Status" src="https://img.shields.io/badge/status-beta-10bfe1?style=flat-square"/>
  <img alt="Versão" src="https://img.shields.io/badge/vers%C3%A3o-26.4.10-10bfe1?style=flat-square"/>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-1f2334?style=flat-square&logo=python&logoColor=FFD43B"/>
  <img alt="CustomTkinter" src="https://img.shields.io/badge/UI-CustomTkinter-1f2334?style=flat-square"/>
  <img alt="Windows" src="https://img.shields.io/badge/Windows-10%2F11-1f2334?style=flat-square&logo=windows&logoColor=white"/>
  <img alt="TSCBr" src="https://img.shields.io/badge/TSCBr-Technology%20Solution%20Company-1f2334?style=flat-square&labelColor=10bfe1"/>
</p>

## O problema

Em equipes de suporte remoto, o AnyDesk é a porta de entrada para atender o cliente. Quando ele trava, fica preso em "conectando" ou perde o vínculo com a rede, o atendimento para, e a correção manual exige parar o serviço, localizar e apagar arquivos de configuração em pastas diferentes do sistema e reiniciar tudo na ordem certa.

Esse procedimento é técnico, demorado e fácil de errar: apagar o arquivo errado leva junto as preferências do usuário, e um passo esquecido deixa o problema intacto. Para quem está do outro lado da linha esperando, cada minuto conta.

O TSCDesk automatiza esse processo com uma interface visual, indicadores de status em tempo real e dois níveis de recuperação, preservando as preferências sempre que possível.

## O que faz

- **Painel de status** com indicadores (verde, amarelo, vermelho) para instalação, estado do AnyDesk, sistema e informações.
- **Resetar AnyDesk:** para o serviço, remove os arquivos de configuração de rede, reinicia o AnyDesk para gerar um novo ID e **preserva** as preferências do usuário (`user.conf`). Intervalo mínimo de 60 segundos entre usos.
- **Forçar reset:** desinstala completamente, limpa arquivos e registro e reinstala do zero a partir do instalador oficial. Disponível uma vez por sessão.
- **Primeira execução assistida:** cria a pasta de trabalho, instala o AnyDesk oficial se necessário e cria atalho na área de trabalho.
- **Log de execução** expansível e **contadores** de resets salvos entre sessões.
- Executa com elevação de administrador (UAC), exigida para controlar o serviço do AnyDesk.

## Capturas

Capturas da interface serão adicionadas em uma próxima versão.

## Stack

Python 3.12 · CustomTkinter · Pillow · PyInstaller (executável único `--onefile`, `--uac-admin`) · APIs do Windows (serviços e registro via `winreg`).

## Como executar

**Executável pronto:** baixe `Reset AnyDesk.exe` em [Releases](../../releases) e execute (o Windows pedirá permissão de administrador).

**A partir do código:**

```powershell
python -m pip install customtkinter pillow
python anydesk_reset.py          # requer prompt como administrador
```

**Gerar o executável:** execute `build.bat`. Ele instala as dependências (customtkinter, pyinstaller, pillow) e gera `Reset AnyDesk.exe` com PyInstaller.

## Escopo da versão pública

- Código-fonte completo do utilitário, script de build e ícone.
- Não acompanham o repositório: logs, histórico de execução e arquivos locais gerados pelo app (`reset-anydesk/`, ignorados pelo git).
- O AnyDesk é baixado exclusivamente do site oficial (`download.anydesk.com`).
- **Uso responsável:** esta ferramenta serve para recuperar instalações com falha. Use o AnyDesk de acordo com os termos de licença do fabricante; uso comercial requer licença paga. AnyDesk é marca registrada da AnyDesk Software GmbH; este projeto é independente e sem afiliação.

## Licença

[MIT](LICENSE)

---

Desenvolvido por **Estevão Santos** · **TSCBr — Technology Solution Company** · [tscbr.com.br](https://www.tscbr.com.br/)
