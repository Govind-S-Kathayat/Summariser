function switchInput(){

let type=document.getElementById("type").value;

document.getElementById("youtubeBox").style.display="none";
document.getElementById("fileBox").style.display="none";
document.getElementById("textBox").style.display="none";


if(type==="youtube"){

document.getElementById("youtubeBox").style.display="block";

}

if(type==="file"){

document.getElementById("fileBox").style.display="block";

}

if(type==="text"){

document.getElementById("textBox").style.display="block";

}

}



async function summarize(){

let type=document.getElementById("type").value;

let model=document.getElementById("model").value;

let form=new FormData();

form.append("type",type);

form.append("model",model);


if(type==="youtube"){

let url=document.getElementById("youtube").value;

if(!url){

alert("Enter YouTube URL");

return;

}

form.append("youtube",url);

}


if(type==="file"){

let file=document.getElementById("file").files[0];

if(!file){

alert("Upload file");

return;

}

form.append("file",file);

}


if(type==="text"){

let text=document.getElementById("text").value;

if(!text){

alert("Enter text");

return;

}

form.append("text",text);

}


document.getElementById("loader").style.display="block";

document.getElementById("output").innerText="";


try{

let response=await fetch(

"/summarize",

{

method:"POST",

body:form

}

);


let data=await response.json();


document.getElementById("loader").style.display="none";


if(data.error){

alert(data.error);

return;

}


document.getElementById("output")

.innerText=data.summary;


document.getElementById("words")

.innerText="Words: "+data.words;


document.getElementById("modelused")

.innerText="Model: "+model;


}
catch(error){

document.getElementById("loader").style.display="none";

alert("Error processing request");

}

}



function copySummary(){

let text=document.getElementById("output").innerText;

if(!text){

alert("No summary");

return;

}

navigator.clipboard.writeText(text);

alert("Summary copied");

}



document.getElementById("download")

.addEventListener("click",function(){

let text=document.getElementById("output").innerText;

if(!text){

alert("No summary");

return;

}

let blob=new Blob(

[text],

{type:"text/plain"}

);

let link=document.createElement("a");

link.href=URL.createObjectURL(blob);

link.download="summary.txt";

link.click();

});