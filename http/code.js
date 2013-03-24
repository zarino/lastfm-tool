function feedback(html, type){
  type = type || 'info'
  if(html==false){
    $('#feedback').empty()
  } else {
    $('#feedback').html(html).removeClass().addClass('text-' + type)
  }
}

function loading(bool){
  if(bool){
    $('#import').addClass('loading').html('Importing&hellip;')
  } else {
    $('#import').removeClass('loading').html('Import <i class="icon-chevron-right"></i>')
  }
}

function progress(percentage){
  if(typeof(percentage)=='number' && percentage >= 0 && percentage <= 100){
    if($('.progress').length){
      var p = $('.progress')
    } else {
      var p = $('<div class="progress progress-danger">').append('<div class="bar">')
      p.appendTo('body')
    }
    if(percentage == 100){
      p.removeClass('active progress-striped')
    } else {
      p.addClass('active progress-striped')
    }
    $('.bar', p).css('width', percentage+'%')
  } else {
    $('.progress').remove()
  }
}

function avatar(img, url){
  if(img==false && typeof(url)=='undefined'){
    $('#avatar').remove()
  } else {
    $('#username').parent().addClass('input-prepend')
    if(img!=''){
      $('<a id="avatar" href="' + url + '" target="_blank"><img src="' + img + '" /></a>').insertBefore('#username')
    } else {
      $('<a id="avatar" class="empty" href="' + url + '" target="_blank"></a>').insertBefore('#username')
    }
  }
}

function trackProgress(){
  scraperwiki.sql('SELECT COUNT(*) AS n FROM recenttracks WHERE user="' + username + '";', function(data){
    var got = data[0]['n']
    feedback("Imported " + numberWithCommas(got) + " of " + numberWithCommas(playcount) + " tracks", 'progress')
    progress(got/playcount*100)
    if(got >= playcount){
      clearTimeout(poll)
      feedback("All done!", 'progress')
    }
  })
}

function numberWithCommas(x) {
  // http://stackoverflow.com/questions/2901102/
  return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

$(function(){

  $('#import').on('click', function(){
    loading(true)
    avatar(false)
    username = $('#username').val()
    $.ajax({
      url: 'http://ws.audioscrobbler.com/2.0/',
      data: {
        method: 'user.getinfo',
        user: username,
        api_key: '12b5aaf2b0f27b4b9402b391c956a88a',
        format: 'json'
      }, dataType: 'json'
    }).done(function(data){
      if('user' in data){
        playcount = data.user.playcount
        avatar(data.user.image[1]['#text'], data.user.url)
        if(playcount == '0'){
          loading(false)
          feedback('<img src="exclamation.png" width="16" height="16" /> That user hasn&rsquo;t listened to anything!', 'error')
        } else {
          $('#username').attr('disabled', true)
          feedback('Starting import&hellip;', 'progress')
          progress(0)
          // Start scraper.py, and background it (end the exec command in a "&")
          // so the script continues to run after the exec call has ended.
          scraperwiki.exec('echo "started"; tool/scraper.py ' + username + ' &> log.txt &', function(data){
            // We assume the script has started.
            // Poll the sqlite endpoint every 5 seconds to monitor for new rows.
            poll = setInterval(trackProgress, 5000)
            // We also need to set the crontab, so the script runs again every day
            scraperwiki.exec('echo "set crontab here"')
          }, function(jqXHR, textStatus, errorThrown){
            console.log('Oh no! Error:', jqXHR.responseText, textStatus, errorThrown)
          })
        }
      } else if('error' in data){
        loading(false)
        avatar(false)
        if(data.message == 'No user with that name was found'){
          feedback('<img src="user-unknown.png" width="16" height="16" /> Sorry, that user doesn&rsquo;t exist.', 'error')
        } else {
          feedback('<img src="exclamation.png" width="16" height="16" /> Unexpected error from Last.fm API: ' + data.message, 'error')
        }
      }
    }).fail(function(){
      feedback('<img src="exclamation.png" width="16" height="16" /> Unable to contact Last.fm API.', 'error')
    })
  })

  $('#username').on('keypress', function(e){
    if(e.which == 13){
      $('#import').trigger('click')
    }
  })

})
