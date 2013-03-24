function feedback(html, type){
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

$(function(){

  $('#import').on('click', function(){
    loading(true)
    avatar(false)
    $.ajax({
      url: 'http://ws.audioscrobbler.com/2.0/',
      data: {
        method: 'user.getinfo',
        user: $('#username').val(),
        api_key: '12b5aaf2b0f27b4b9402b391c956a88a',
        format: 'json'
      }, dataType: 'json'
    }).done(function(data){
      if('user' in data){
        avatar(data.user.image[1]['#text'], data.user.url)
        if(data.user.playcount == '0'){
          loading(false)
          feedback('<img src="exclamation.png" width="16" height="16" /> That user hasn&rsquo;t listened to anything!', 'error')
        } else {
          feedback(false)
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
