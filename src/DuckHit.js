// One geometric contract for reactions and the window input region. No image reads.
function ellipse(p,x,y,rx,ry){return Math.pow((p.x-x)/rx,2)+Math.pow((p.y-y)/ry,2)<=1;}
function rect(p,left,top,right,bottom){return p.x>=left&&p.x<=right&&p.y>=top&&p.y<=bottom;}
function oval(item,zone,x,y,rx,ry){return {item:item,zone:zone,x:x,y:y,rx:rx,ry:ry};}
function box(item,zone,x,y,w,h){return {item:item,zone:zone,x:x+w/2,y:y+h/2,rx:w/2,ry:h/2,box:true};}
function polygon(item,zone,points){return {item:item,zone:zone,points:points};}
function inside(p,points){var hit=false;for(var i=0,j=points.length-1;i<points.length;j=i++){
    var a=points[i],b=points[j];if((a[1]>p.y)!==(b[1]>p.y)&&p.x<(b[0]-a[0])*(p.y-a[1])/(b[1]-a[1])+a[0])hit=!hit;}return hit;}
function region(shapes,target,x,y){
    for(var s of shapes){var p=s.item.mapFromItem(target,x,y);
        if(s.points?inside(p,s.points):s.box?rect(p,s.x-s.rx,s.y-s.ry,s.x+s.rx,s.y+s.ry):ellipse(p,s.x,s.y,s.rx,s.ry))return s.zone;}
    return "";
}
function polygons(shapes,target){return shapes.map(function(s){
    if(s.points)return s.points.map(function(p){return s.item.mapToItem(target,p[0],p[1]);});
    var points=[],n=s.box?4:24;
    for(var i=0;i<n;i++){var a=i*2*Math.PI/n;
        var x=s.box?([-1,1,1,-1][i])*s.rx:Math.cos(a)*s.rx;
        var y=s.box?([-1,-1,1,1][i])*s.ry:Math.sin(a)*s.ry;
        points.push(s.item.mapToItem(target,s.x+x,s.y+y));}
    return points;
});}
// Scan conversion of transformed simple figures, in logical coordinates.
// Two-pixel bands cost no texture downloads and leave large transparent corners clear.
function bands(polys,step){
    var result=[],low=Infinity,high=-Infinity;
    for(var poly of polys)for(var p of poly){low=Math.min(low,p.y);high=Math.max(high,p.y);}
    for(var y=Math.floor(low);y<high;y+=step){
        var spans=[];
        for(var poly of polys){
            var xs=[];
            // Include band edges as well as its centre to avoid cracks while rotated.
            for(var scan of [y+.01,y+step/2,y+step-.01])for(var i=0;i<poly.length;i++){
                var a=poly[i],b=poly[(i+1)%poly.length];
                if((a.y<=scan&&b.y>scan)||(b.y<=scan&&a.y>scan))xs.push(a.x+(scan-a.y)*(b.x-a.x)/(b.y-a.y));
            }
            if(xs.length)spans.push([Math.floor(Math.min.apply(null,xs)),Math.ceil(Math.max.apply(null,xs))]);
        }
        spans.sort(function(a,b){return a[0]-b[0];});var merged=[];
        for(var span of spans){var last=merged[merged.length-1];if(last&&span[0]<=last[1])last[1]=Math.max(last[1],span[1]);else merged.push(span);}
        for(var span of merged)result.push({x:span[0],y:y,width:span[1]-span[0],height:step});
    }
    return result;
}
