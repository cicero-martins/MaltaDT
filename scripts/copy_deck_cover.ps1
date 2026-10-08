# Gives a generated deck the cover held in docs/deck_cover.pptx, through
# PowerPoint. The cover carries a photograph of Valletta recoloured in
# PowerPoint and two institutional marks, none of which the pptxgenjs generators
# reproduce. The first slide of the target is replaced by the cover, and the
# photograph is repeated behind the last slide.
#
#     powershell -File copy_deck_cover.ps1 <cover deck> <deck to receive it>
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

# The photograph is the picture that spans the slide. msoPicture is 13 and
# msoSendToBack is 1.
$photo = $null
foreach ($sh in $pres.Slides.Item(1).Shapes) {
    if ($sh.Type -eq 13 -and $sh.Width -gt 0.9 * $pres.PageSetup.SlideWidth) { $photo = $sh }
}
if ($photo) {
    $last = $pres.Slides.Item($pres.Slides.Count)
    $photo.Copy()
    $pasted = $last.Shapes.Paste()
    $pasted.Left = $photo.Left
    $pasted.Top = $photo.Top
    $pasted.ZOrder(1)
}
$pres.Save()
"slides: " + $pres.Slides.Count
$pres.Close()
