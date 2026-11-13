const fs = require('node:fs');
const vm = require('node:vm');
const path = 'C:/Users/mille/.codex/visualizations/2026/10/06/01a113a2-442d-71a1-9d5a-6bb93a39772f/mackenzie-palette.html';
const output = 'C:/GrandTour/Art/Export/LevelPalette/palette-01/';
const image = key => 'data:image/jpeg;base64,' + fs.readFileSync(output + key + '.jpg').toString('base64');
let html = fs.readFileSync(path, 'utf8');
if (!html.includes('__INITIAL_IMAGE__')) throw Error('Fragment has already been packaged');
html = html.replace('__INITIAL_IMAGE__', image('natural')).replace('__PALETTE_IMAGES__', JSON.stringify({current:image('current'),golden:image('golden'),muted:image('muted'),natural:null}));
if (Buffer.byteLength(html) >= 1000000) throw Error('Fragment exceeds size limit');
const photo = {src:image('natural'),style:{}};
const caption = {};
const check = {checked:false,addEventListener(type,fn){this[type]=fn;}};
const buttons = ['current','natural','golden','muted'].map(palette => ({dataset:{palette},attrs:{},setAttribute(k,v){this.attrs[k]=v;},addEventListener(type,fn){this[type]=fn;}}));
const root = {querySelector:q => ({'.landscape':photo,'figcaption':caption,'[data-value-check]':check})[q],querySelectorAll:() => buttons};
const events = {};
const window = {addEventListener:(name,fn)=>events[name]=fn};
vm.runInNewContext(html.match(/<script>([\s\S]*?)<\/script>/)[1], {document:{getElementById:()=>root},window});
for (const button of buttons) {
  button.click();
  if (photo.src !== image(button.dataset.palette) || button.attrs['aria-pressed']!=='true') throw Error('Palette selection failed');
}
check.checked=true; check.change();
if (photo.style.filter !== 'grayscale(1)') throw Error('Value check failed');
events['openai:set_globals']({detail:{globals:{widgetState:{modelContent:{palette:'natural'},privateContent:{grayscale:false}}}}});
if (photo.src!==image('natural') || photo.style.filter!=='') throw Error('State restore failed');
fs.writeFileSync(path,html);
console.log(JSON.stringify({file:path,bytes:Buffer.byteLength(html),checks:['four palette switches','value toggle','saved-state restore']}));
