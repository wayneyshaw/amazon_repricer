`import Ember from 'ember'`

ProgressBar = Ember.View.extend
    classNames: ['progress']
    template: (->
        '<div class="progress-bar" role="progressbar" aria-valuenow="60" aria-valuemin="0" aria-valuemax="100" style="width: 0%; transition: none;">
                    <div class=percentInside style="color: black; margin: 0px 5px;">0%</div>
                  </div>').observes('percent')
    percent: 0

    percentDidChange: (->
        percent = @get 'percent' || 0
        @$('.progress-bar').css 'width', percent + '%'
        @$('div.percentInside').html(percent.toFixed(0) + '%')
        if percent is 0
            debugger
            @$('div.percentInside').css 'margin', '0px', '5px'


    ).observes('percent')

`export default ProgressBar`