param([Parameter(Mandatory=$true)][string]$Dir)

# Export every .docx in $Dir to PDF with Word COM and report page/word/table/figure counts.
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$results = @()

Get-ChildItem -Path $Dir -Filter '*.docx' | Sort-Object Name | ForEach-Object {
    $src = $_.FullName
    $dst = [System.IO.Path]::ChangeExtension($src, '.pdf')
    try {
        $doc = $word.Documents.Open($src, $false, $true)
        $doc.Fields.Update() | Out-Null
        $doc.ExportAsFixedFormat($dst, 17)
        $pages  = $doc.ComputeStatistics(2)   # wdStatisticPages
        $words  = $doc.ComputeStatistics(0)   # wdStatisticWords
        $tables = $doc.Tables.Count
        $shapes = $doc.InlineShapes.Count
        $doc.Close($false)
        $results += [pscustomobject]@{
            File = $_.Name; Pages = $pages; Words = $words; Tables = $tables; Figures = $shapes
        }
    } catch {
        $results += [pscustomobject]@{
            File = $_.Name; Pages = 'ERROR'; Words = $_.Exception.Message; Tables = ''; Figures = ''
        }
    }
}
$word.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
$results | Format-Table -AutoSize | Out-String -Width 200
