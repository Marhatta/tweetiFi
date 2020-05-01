  let{PythonShell}=require('python-shell');
  const fs=require('fs-extra');
  var app = require('electron').remote;
  var dialog = app.dialog;

  var preprocess=document.getElementById('preprocess');
  var minimize=document.getElementById('minimize');
  var maximize=document.getElementById('maximize');
  var close=document.getElementById('close');
  var terminal=document.getElementById('terminal');
  var open_terminal=document.getElementById('open_terminal');
  var filterLanguage=document.getElementById('filterLanguage');
  var filterRetweets=document.getElementById('filterRetweets');
  var irrelevantData=document.getElementById('irrelevantData');
  var ngrams=document.getElementById('ngrams');
  var spinner=document.getElementById('spinner');
  var showPreprocessErrors=document.getElementById('showPreprocessErrors');
  var warning=document.getElementById('warning');
  var flbar=document.getElementById('flbar');
  var flbar1=document.getElementById('flbar1');
  var flbar2=document.getElementById('flbar2');
  var flbar3=document.getElementById('flbar3');
  var executionTime=document.getElementById('executionTime');
  var deleteFolders=document.getElementById('deleteFolders');
  var ctx = document.getElementById('myChart').getContext('2d');
  var terminalLine=0;//line number on terminal window

  var pathToData2='./Data2';
  var pathToData3='./Data3';
  var pathToData4='./Data4';
  var pathToData5='./Data5';



  filterLanguage.style.display='none';//initially display tick icon to none
  filterRetweets.style.display='none';
  irrelevantData.style.display='none';
  ngrams.style.display='none';
  warning.style.display='none';//initially no warning icon
  //deleteFolders.style.display='none';

  var Data1='';

  //folder selection
  document.getElementById('selectFolder').addEventListener('click',()=>{

    dialog.showOpenDialog({
      title:'Select a folder',
      properties:['openDirectory']
    },(folderPaths)=>{
      if(folderPaths === undefined){
        document.getElementById('showPath').innerHTML='Nothing was returned';

      }else{
        document.getElementById('showPath').innerHTML=folderPaths;
        Data1=folderPaths;
      }
    });
  });




  //folder deletion
  deleteFolders.addEventListener('click',()=>{
    fs.remove(pathToData2,err=>{
      if (err) return console.error(err);

      console.log('success');
    });

    fs.remove(pathToData3,err=>{
      if (err) return console.error(err);

      console.log('success');
    });

    fs.remove(pathToData4,err=>{
      if (err) return console.error(err);

      console.log('success');
    });

    fs.remove(pathToData5,err=>{
      if (err) return console.error(err);

      console.log('success');
      showSnackbar();

    });

  })




    let tweetsProcessCount = [];



  preprocess.addEventListener('click',function(){ //on click preprocess

    //options
    //P.S - do not take options out of event listener
    var options_for_languagefilter={
      mode: 'text',
      encoding:'utf8',
      pythonPath:'python2.7',
      pythonOptions: ['-u'], //get print results in real time
      scriptPath: './',
      args: [Data1, 'Data2', 'guess-language-0.2','English','False','Data2', 'Data3', 'True','3','False','Data3','Data4','False','Data4','Data5','all','False']
    }


    flbar.style.width=0 + "%"; //set width to zero
    flbar1.style.width=0 + "%";
    flbar2.style.width=0 + "%";
    flbar3.style.width=0 + "%";
    spinner.style.display='block';//display spinner on preprocessing
    filterLanguage.style.display='none';
    filterRetweets.style.display='none';
    irrelevantData.style.display='none';
    executionTime.style.display='none';
    ngrams.style.display='none';
    warning.style.display='none';

    let width=1;
    let preprocessingStartTime=new Date().getSeconds();
    let pyshell = new PythonShell('languagefilter.py',options_for_languagefilter);
    let flagForCount = 0;

    pyshell.on('message',function(message){
      terminalLine++;

      if(flagForCount == 1)
      {
        tweetsProcessCount.push(parseInt(message));
        flagForCount = 0;

        if(tweetsProcessCount.length===4)
        {
          showGraph();
        }

      }
      else if(message==='Finishing...'){
        flagForCount = 1;
        flbar.style.width='100'+'%';
        flbar.style.transition='.5s linear';
        filterLanguage.style.display='block';
        let line=document.createElement('p');
        line.innerHTML= terminalLine +" "+ message;
        terminal.append(line);

      }
      else if(message==='RetweetsDone'){
        flagForCount = 1;
        flbar1.style.width='100'+'%';
        flbar1.style.transition='.5s linear';
        filterRetweets.style.display='block';
        let line=document.createElement('p');
        line.innerHTML= terminalLine +" "+ message;
        terminal.append(line);


      }
      else if(message==='TaggedFinishing'){
        flagForCount = 1;
        flbar2.style.width='100'+'%';
        flbar2.style.transition='.5s linear';
        irrelevantData.style.display='block';
        let line=document.createElement('p');
        line.innerHTML= terminalLine +" "+ message;
        terminal.append(line);


      }
      else if(message==='NGramsFinishing'){
        flagForCount = 1;
        flbar3.style.width='100'+'%';
        flbar3.style.transition='.5s linear';
        ngrams.style.display='block';
        spinner.style.display='none';
        let preprocessingEndTime=new Date().getSeconds();
        let timeDiff = (preprocessingEndTime-preprocessingStartTime) < 0 ?
                          60-(-(preprocessingEndTime-preprocessingStartTime)):
                          (preprocessingEndTime-preprocessingStartTime);       
        executionTime.innerHTML='Execution Time is ' + timeDiff +' seconds';
        executionTime.style.display='block';
        let line=document.createElement('p');
        line.innerHTML= terminalLine +" "+ message+" "+" Language Filter:"+tweetsProcessCount[0]+" Retweets Filtered:"+tweetsProcessCount[1]+ " Tagged Tweets:"+tweetsProcessCount[2];
        terminal.append(line);

      }
      else{
        let line=document.createElement('p');
        line.innerHTML= terminalLine +" "+ message;
        terminal.append(line);
        if(width<90){
          width+=0.25;
          flbar.style.width = width + '%';
          flbar.style.transition='2s linear';

          if(message.includes('already exists')){
            line.style.background='#F36242';
            showPreprocessErrors.innerHTML=' See Line '+ terminalLine+' on Terminal Screen';
            warning.style.display='block';
            showPreprocessErrors.style.display='block';
            spinner.style.display='none';
          }else{ //else show no errors
            warning.style.display='none';
            showPreprocessErrors.style.display='none';
          }

        }
      }
      ScrollDiv();
    });


  });


  function ScrollDiv(){

    if(document.getElementById('terminal').scrollTop<(document.getElementById('terminal').scrollHeight-document.getElementById('terminal').offsetHeight)){
      document.getElementById('terminal').scrollTop=document.getElementById('terminal').scrollTop+50
    }
  }




  //terminal dom
  open_terminal.style.display='none';

  minimize.addEventListener('click',function(){
    terminal.style.height='30px';
  });

  maximize.addEventListener('click',function(){
    terminal.style.height=(terminal.style.height==='100vh' ? '340px' : '100vh');
  });

  close.addEventListener('click',function(){
    terminal.style.display='none';
    open_terminal.style.display='block';

  });

  open_terminal.addEventListener('click',function(){
    terminal.style.display='block';
    open_terminal.style.display='none';

  });



  //bar graph

  function showGraph()
  {
    let chart = new Chart(ctx, {
    // The type of chart we want to create
    type: 'bar',

    // The data for our dataset
    data: {
      labels: ["Languages", "irrelevantData", "Tagging", "Retweets"],
      datasets: [{
        label: "Preprocessing Count",
        backgroundColor: ['rgba(255, 99, 132, 0.2)',
        'rgba(54, 162, 235, 0.2)',
        'rgba(255, 206, 86, 0.2)',
        'rgba(75, 192, 192, 0.2)'],
        borderColor: ['rgba(255,99,132,1)',
        'rgba(54, 162, 235, 1)',
        'rgba(255, 206, 86, 1)',
        'rgba(75, 192, 192, 1)'],
        data: [tweetsProcessCount[0], tweetsProcessCount[1], tweetsProcessCount[2], tweetsProcessCount[3]]
      }]
    },

    // Configuration options go here
    options: {
      responsive:true,
      scales: {
        yAxes: [{
          ticks: {
            beginAtZero:true
          }
        }]
      }
    }

  });


  }

  // snackbar

  function showSnackbar() {
    // Get the snackbar DIV
    var x = document.getElementById("snackbar");
    x.innerHTML='Deleted';
    // Add the "show" class to DIV
    x.className = "show";

    // After 3 seconds, remove the show class from DIV
    setTimeout(function(){ x.className = x.className.replace("show", ""); }, 3000);
  }



  var contentEditor=document.getElementById('content-editor');
  var contentEditorWrapper=document.getElementById('contentEditorWrapper');
  contentEditorWrapper.style.display='none';

  document.getElementById('closeContentEditor').addEventListener('click',()=>{
    contentEditorWrapper.style.display='none';
  });

  document.getElementById('select-file').addEventListener('click',function(){
    dialog.showOpenDialog(function (fileNames) {
      if(fileNames === undefined){
        console.log("No file selected");
      }else{
        document.getElementById("actual-file").value = fileNames[0];
        readFile(fileNames[0]);
      }
    });
  },false);

  document.getElementById('save-changes').addEventListener('click',function(){
    var actualFilePath = document.getElementById("actual-file").value;

    if(actualFilePath){
      saveChanges(actualFilePath,contentEditor.value);
    }else{
      alert("Please select a file first");
    }
  },false);

  document.getElementById('delete-file').addEventListener('click',function(){
    var actualFilePath = document.getElementById("actual-file").value;

    if(actualFilePath){
      deleteFile(actualFilePath);
      document.getElementById("actual-file").value = "";
      contentEditor.value = "";
    }else{
      alert("Please select a file first");
    }
  },false);

  document.getElementById('create-new-file').addEventListener('click',function(){

    var content = '';

    dialog.showSaveDialog(function (fileName) {
      if (fileName === undefined){
        console.log("You didn't save the file");
        return;
      }

      fs.writeFile(fileName, content, function (err) {
        if(err){
          alert("An error ocurred creating the file "+ err.message)
        }

        alert("The file has been succesfully saved");
      });
    });
  },false);

  function readFile(filepath) {
    fs.readFile(filepath, 'utf-8', function (err, data) {
      if(err){
        alert("An error ocurred reading the file :" + err.message);
        return;
      }
      contentEditorWrapper.style.display='block';
      contentEditor.value = data;
    });
  }

  function deleteFile(filepath){
    fs.exists(filepath, function(exists) {
      if(exists) {
        // File exists deletings
        fs.unlink(filepath,function(err){
          if(err){
            alert("An error ocurred updating the file"+ err.message);
            console.log(err);
            return;
          }
          contentEditorWrapper.style.display='none';
          alert('File Deleted');

        });
      } else {
        alert("This file doesn't exist, cannot delete");
      }
    });
  }

  function saveChanges(filepath,content){
    fs.writeFile(filepath, content, function (err) {
      if(err){
        alert("An error ocurred updating the file"+ err.message);
        console.log(err);
        return;
      }

      alert("The file has been succesfully saved");
    });
  }
