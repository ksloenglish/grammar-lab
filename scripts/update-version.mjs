import { writeFileSync } from 'node:fs';
const parts = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Asia/Hong_Kong', year: '2-digit', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23'
}).formatToParts(new Date());
const value = type => parts.find(part => part.type === type).value;
const version = `v${value('year')}${value('month')}${value('day')}-${value('hour')}${value('minute')}${value('second')}`;
writeFileSync(new URL('../site/version.js', import.meta.url), `// Deployment timestamp in Hong Kong Time (UTC+8). This is the single version source.\nexport const VERSION = '${version}';\n`);
console.log(version);
