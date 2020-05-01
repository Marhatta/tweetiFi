  let {PythonShell}=require('python-shell');
  const fs=require('fs-extra');
  var app = require('electron').remote;
  var dialog = app.dialog;

  var classify=document.getElementById('classify');
  var minimize=document.getElementById('minimize');
  var maximize=document.getElementById('maximize');
  var close=document.getElementById('close');
  var terminal=document.getElementById('terminal');
  var open_terminal=document.getElementById('open_terminal');
  var filterLanguage=document.getElementById('filterLanguage');
  var filterRetweets=document.getElementById('filterRetweets');
  var spinner=document.getElementById('spinner');
  var showPreprocessErrors=document.getElementById('showPreprocessErrors');
  var warning=document.getElementById('warning');
  var flbar=document.getElementById('flbar');
  var flbar1=document.getElementById('flbar1');
  var executionTime=document.getElementById('executionTime');
  var deleteFolders=document.getElementById('deleteFolders');
  var terminalLine=0;//line number on terminal window
  var randomForestResult=document.getElementById('randomForestResult');
  var svmResult=document.getElementById('svmResult');
  var processingTestTweet=document.getElementById('processingTestTweet');
  var classifying=document.getElementById('classifying');

  var pathToData6='./Data6';
  var pathToDataTest2='./DataTest2';

  var processingStatus=['Processing Test Tweet...','Classifying...'];

  filterLanguage.style.display='none';//initially display tick icon to none
  filterRetweets.style.display='none';
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
        DataTest=folderPaths;

      }
    });


  });




  //folder deletion
  deleteFolders.addEventListener('click',()=>{
  fs.remove(pathToData6,err=>{
      if (err) return console.error(err);

      console.log('success');
    });

    fs.remove(pathToDataTest2,err=>{
      if (err) return console.error(err);

      console.log('success');
      showSnackbar();

    });

  })







  classify.addEventListener('click',function(){ //on click preprocess

    //options
    //P.S - do not take options out of event listener
      var options_for_classification={
            mode: 'text',
            encoding:'utf8',
            pythonPath:'python2.7',
            pythonOptions: ['-u'], //get print results in real time
            scriptPath: './',
            args: [DataTest, 'DataTest2','all','False','Data5','Data6','20','DataTest2','1','3','50','all','100','100','False']
      }


    processingTestTweet.innerHTML=processingStatus[0];
    flbar.style.width=0 + "%"; //set width to zero
    flbar1.style.width=0 + "%";
    spinner.style.display='block';//display spinner on preprocessing
    filterLanguage.style.display='none';
    filterRetweets.style.display='none';
    warning.style.display='none';
    showPreprocessErrors.style.display='none';
    executionTime.style.display='none'

    let width=1;
    let preprocessingStartTime=new Date().getSeconds();
    let pyshell2 = new PythonShell('rfclassy.py',options_for_classification);

    var countforResult = 0;
    var resultsOfClassifiers = [];
    pyshell2.on('message',function(message){
        terminalLine++;
        if(message==='resultarecoming')
        {
          processingTestTweet.style.display='none';
          classifying.innerHTML=processingStatus[1];
          countforResult++;
        }
        else if(countforResult>=1 && countforResult<=4)
        {
          if(countforResult%2!=0)
          {
            resultsOfClassifiers.push(message);
          }
          countforResult++;
          let line=document.createElement('p');
          line.innerHTML= terminalLine +" "+ message;
          terminal.append(line);
        }
        else if(message==='NgramsOfTestTweetProcessed'){
          flbar.style.width='100'+'%';
          flbar.style.transition='.5s linear';
          filterLanguage.style.display='block';

        }
        else if(message==='Finishing ... ;)'){
          flbar1.style.width='100'+'%';
          flbar1.style.transition='.5s linear';
          spinner.style.display='none';
          filterRetweets.style.display='block';
          classifying.style.display='none';


          let line=document.createElement('p');
          line.innerHTML= terminalLine +" "+ message;
          terminal.append(line);
          ScrollDiv();

          let preprocessingEndTime=new Date().getSeconds();
          let timeDiff = (preprocessingEndTime-preprocessingStartTime) < 0 ?
                          60-(-(preprocessingEndTime-preprocessingStartTime)):
                          (preprocessingEndTime-preprocessingStartTime);
          executionTime.innerHTML='Execution Time is ' + timeDiff +' seconds';
          executionTime.style.display='block';

          randomForestResult.innerHTML='<strong>Random Forest :</strong> ' + resultsOfClassifiers[0];
          svmResult.innerHTML='<strong>SVM : </strong>' + resultsOfClassifiers[1];

        }
        else{
          let line=document.createElement('p');

          line.innerHTML= terminalLine +" "+ message;
          terminal.append(line);

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
