# Replaces the first slide of a deck by the first slide of another, through
# PowerPoint. The cover of the full concept deck carries a photograph recoloured
# in PowerPoint and two institutional marks, none of which the pptxgenjs
# generators reproduce, so the short deck takes its cover from the full one.
#
#     powershell -File copy_deck_cover.ps1 <deck with the cover> <deck to receive it>
#
# Both paths are absolute. Any PowerPoint instance already running is reused and
# left open.
param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Target
)
$pp = New-Object -ComObject PowerPoint.Application
$pres = $pp.Presentations.Open($Target, $false, $false, $false)
$pres.Slides.InsertFromFile($Source, 0, 1, 1) | Out-Null
$pres.Slides.Item(2).Delete()
$pres.Save()
"slides: " + $pres.Slides.Count
$pres.Close()
