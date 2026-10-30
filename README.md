# BIM Coder Kit

Extensão pessoal para o [pyRevit](https://pyrevitlabs.io/) com ferramentas e atalhos para fluxos de trabalho no Autodesk Revit. A interface está organizada em painéis de anotação, desenvolvimento, elétrica, hidrossanitário, materiais e vistas.

## Requisitos

- Windows
- Autodesk Revit
- pyRevit instalado e configurado para a versão do Revit em uso

As ferramentas usam a API do Revit e devem ser executadas dentro do Revit pelo pyRevit; não são scripts Python independentes. As versões compatíveis do Revit/pyRevit ainda não estão documentadas.

## Instalação

1. Instale o Autodesk Revit e o pyRevit.
2. No PowerShell, clone esta extensão dentro da pasta de extensões do pyRevit:

   ```powershell
   $extensions = Join-Path $env:APPDATA 'pyRevit\Extensions'
   New-Item -ItemType Directory -Force -Path $extensions | Out-Null
   git clone https://github.com/alexsandrejr/alex-bim-kit.git (Join-Path $extensions 'BIM Coder Kit.extension')
   ```

3. Abra ou reinicie o Revit e atualize/carregue novamente as extensões do pyRevit.

## Atualização

Para obter alterações publicadas:

```powershell
$extension = Join-Path $env:APPDATA 'pyRevit\Extensions\BIM Coder Kit.extension'
git -C $extension pull
```

Depois, atualize as extensões no pyRevit ou reinicie o Revit.

## Conteúdo

- **Annotate**: renumeração de elementos e viewports.
- **Elétrica**: ferramentas para eletrodutos.
- **Hidrossanitário**: ferramentas para tubos.
- **Views**: ferramentas de vistas, tabelas, seleção e filtros.
- **Materiais**: atalhos para documentação, fóruns, e-books e tutoriais.
- **Desenvolvimento**: comandos de teste.
- `hooks/` e `lib/`: hooks e módulos auxiliares compartilhados.

## Observações

- O conteúdo do projeto está em português e ainda inclui comandos identificados como testes/exemplos.
- O ambiente virtual local (`.venv`), arquivos de IDE, credenciais e certificados não fazem parte do repositório.
- Não há instruções de build ou testes automatizados documentadas; os comandos devem ser validados em um modelo de trabalho no Revit antes do uso em produção.
