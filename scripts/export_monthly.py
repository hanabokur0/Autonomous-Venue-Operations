import fs from 'node:fs/promises';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const [source, target] = process.argv.slice(2);
if (!source || !target) {
  console.error('Usage: node scripts/export_monthly.mjs monthly.json monthly.xlsx');
  process.exit(2);
}
const data = JSON.parse(await fs.readFile(source, 'utf8'));
const wb = Workbook.create();
const sheet = wb.worksheets.add('月間予定表');
sheet.showGridLines = false;
sheet.tabColor = '#1e3a5f';
sheet.getRange('B2').values = [[`${data.year}年${data.month}月 貸し出し予定表`]];
sheet.getRange('B2').format.font = {name:'Arial', size:15, bold:true, color:'#17324d'};
sheet.getRange('B3').values = [[`時間帯: ${data.timezone} ／ 確定予約のみ`]];
sheet.getRange('B3').format.font = {name:'Arial', size:10, color:'#64748b'};

const headers = ['日付','曜日','施設','利用企業','開始','終了','予約ID','状態'];
sheet.getRange('B5:I5').values = [headers];
sheet.getRange('B5:I5').format = {
  fill:'#1f4e68', font:{name:'Arial',size:10,bold:true,color:'#ffffff'},
  rowHeight:27, verticalAlignment:'center', horizontalAlignment:'center'
};

const days = ['日','月','火','水','木','金','土'];
const rows = [];
const venues = Object.fromEntries(data.venues.map(v=>[v.id,v.name]));
for (let day=1; day<=data.days; day++) {
  const iso = `${data.year}-${String(data.month).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
  const weekday = days[new Date(Date.UTC(data.year,data.month-1,day)).getUTCDay()];
  for (const venue of data.venues) {
    const matching = data.bookings.filter(b=>b.venue_id===venue.id &&
      b.starts_local.slice(0,10)<=iso && b.ends_local.slice(0,10)>=iso &&
      !(b.ends_local.slice(0,10)===iso && b.ends_local.slice(11,16)==='00:00'));
    if (!matching.length) rows.push([iso,weekday,venue.name,'空き','—','—','—','空き']);
    for (const b of matching) {
      const start = b.starts_local.slice(0,10)===iso ? b.starts_local.slice(11,16) : '00:00';
      const finish = b.ends_local.slice(0,10)===iso ? b.ends_local.slice(11,16) : '24:00';
      rows.push([iso,weekday,venue.name,b.tenant_id,start,finish,b.id,'予約済']);
    }
  }
}
sheet.getRangeByIndexes(5,1,rows.length,8).values=rows;
const last=5+rows.length;
sheet.getRange(`B6:I${last}`).format.font={name:'Arial',size:10,color:'#1e293b'};
sheet.getRange(`B6:I${last}`).format.rowHeight=22;
sheet.getRange(`B6:I${last}`).format.verticalAlignment='center';
for(let i=0;i<rows.length;i++) {
  if(rows[i][7]==='予約済') sheet.getRange(`I${i+6}`).format.fill='#dcfce7';
  if(rows[i][7]==='空き') sheet.getRange(`I${i+6}`).format.fill='#f1f5f9';
  if(rows[i][1]==='日') sheet.getRange(`C${i+6}`).format.font={name:'Arial',size:10,color:'#dc2626'};
  if(rows[i][1]==='土') sheet.getRange(`C${i+6}`).format.font={name:'Arial',size:10,color:'#2563eb'};
}
const widths=[105,55,170,160,65,65,200,80];
for(let i=0;i<8;i++) sheet.getRangeByIndexes(4,i+1,rows.length+1,1).format.columnWidthPx=widths[i];
sheet.freezePanes.freezeRows(5);
const detail=wb.worksheets.add('予約明細');
detail.showGridLines=false;
detail.getRange('A1:F1').values=[['予約ID','施設','利用企業','開始日時','終了日時','状態']];
detail.getRange('A1:F1').format={fill:'#1f4e68',font:{name:'Arial',bold:true,color:'#ffffff'}};
const details=data.bookings.map(b=>[b.id,venues[b.venue_id]??b.venue_id,b.tenant_id,b.starts_local,b.ends_local,b.status]);
if(details.length) detail.getRangeByIndexes(1,0,details.length,6).values=details;
detail.getRange('A:A').format.columnWidthPx=200;
detail.getRange('B:C').format.columnWidthPx=160;
detail.getRange('D:E').format.columnWidthPx=220;
detail.getRange('F:F').format.columnWidthPx=90;
wb.recalculate();
const check=await wb.inspect({kind:'table',range:'月間予定表!B2:I10',tableMaxRows:10,tableMaxCols:8,maxChars:2500});
console.log(check.ndjson);
const problems=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A',options:{useRegex:true,maxResults:50}});
console.log(problems.ndjson);
const output=await SpreadsheetFile.exportXlsx(wb);
await output.save(target);
if(process.env.AVO_PREVIEW) {
  const img=await wb.render({sheetName:'月間予定表',range:'B2:I17',scale:1.5,format:'png'});
  await fs.writeFile(process.env.AVO_PREVIEW,new Uint8Array(await img.arrayBuffer()));
}
