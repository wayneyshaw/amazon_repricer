`import Ember from 'ember'`

InquiryController = Ember.ObjectController.extend(
    DEFAULT_SKU_PREFIX: 'TECHROVER_SKU'

    skuPrefix: ''
    discountPercent: ''
    minimumPrice: ''

    selectedCategory: 'Laptop and Netbook Computer Batteries'
    categories: ['Laptop and Netbook Computer Batteries']

    pagesToReturn: ''

    selectedCountry: 'USA'
    countries: ['USA', 'UK', 'Canada']

    searchPhrases: ''

    percentOfPagesFetched: 0

    finalCleanedList: []

    threeCell: ''
    fourCell: ''
    sixCell: ''
    eightCell: ''
    nineCell: ''
    twelveCell: ''

    threeCellOriginal: ''
    fourCellOriginal: ''
    sixCellOriginal: ''
    eightCellOriginal: ''
    nineCellOriginal: ''
    twelveCellOriginal: ''

    actions:
        searchButtonPressed: (->
            topContext = this
            topContext.set('percentOfPagesFetched', 0)

            # Run a ton of queries asynchronously.
            _get = (url) ->
                # Return a new promise.
                return new Promise(
                    (resolve, reject) ->
                        # Do the usual XHR stuff
                        req = new XMLHttpRequest()
                        req.open('GET', url)

                        req.onload = () ->
                            # This is called even on 404 etc so check the status
                            if (req.status == 200)
                                # Resolve the promise with the response text
                                resolve(req.response);
                            else
                                # Otherwise reject with the status text which will hopefully be a meaningful error
                                reject(Error(req.statusText))

                        # Handle network errors
                        req.onerror = () ->
                            reject(Error("Network Error"))

                        # Make the request
                        req.send()
                )

            _parseResponses = (responseList) ->
                # Use JQuery to pull out the parts we care about.
                debugger
                topContext.set('percentOfPagesFetched', 0)
                chunkSize = 2
                responseStartIndex = 0
                itemList = []
                return new Promise(
                    (resolve, reject) ->
                        processResponsesEfficiently = () ->
                            endIndex = Math.min(responseStartIndex + chunkSize, responseList.length)
                            for index in [responseStartIndex...endIndex]
                                responseDom = document.createElement('div')
                                responseDom.innerHTML = responseList[index]
                                for currentDiv, i in responseDom.querySelectorAll('div.prod')
                                    debugger
                                    currentItem =
                                        rank: currentDiv.getAttribute('id')
                                        asin: currentDiv.getAttribute('name')
                                        url: currentDiv.querySelector('h3 a').getAttribute('href')
                                        title: currentDiv.querySelector('h3 a span').getAttribute('title') || currentDiv.querySelector('h3 a span').innerText
                                        imageUrl: currentDiv.querySelector('.image img').getAttribute('src')

                                    firstPrice = currentDiv.querySelector('li.newp span')
                                    secondPrice = currentDiv.querySelector('li span.price')
                                    if firstPrice
                                        currentItem['price'] = firstPrice.innerText
                                    else if secondPrice
                                        currentItem['price'] = secondPrice.innerText
                                    else
                                        currentItem['price'] = null
                                    rating = currentDiv.querySelector('.asinReviewsSummary a')
                                    currentItem['rating'] = if rating then rating.getAttribute('alt') else null
                                    reviewsCount = currentDiv.querySelector('.rvwCnt a')
                                    currentItem['reviewsCount'] = if reviewsCount then reviewsCount.innerText else null
                                    sellersCount = currentDiv.querySelector('.med.mkp2 a[href*="new"] .grey')
                                    currentItem['sellersCount'] = if sellersCount then sellersCount.innerText else null

                                    itemList.push(currentItem)
                                responseStartIndex += 1
                            topContext.set('percentOfPagesFetched', (responseStartIndex / responseList.length) * 100)
                            if responseStartIndex < responseList.length
                                setTimeout(processResponsesEfficiently, 25)
                            else
                                resolve(itemList)
                        processResponsesEfficiently()
                 )

            amazon_requests_promise = new Promise(
                (resolve, reject) ->
                    pagesToReturn = if topContext.pagesToReturn is '' then 1 else parseInt(topContext.pagesToReturn)
                    searchPhrases = topContext.searchPhrases.split('\n').filter((w) -> return w isnt '')
                    selectedCountry = topContext.selectedCountry

                    numRequestsToMake = searchPhrases.length * pagesToReturn
                    numRequestsReturned = 0
                    requestDataToReturn = []

                    return unless searchPhrases.length > 0

                    for phrase in searchPhrases
                        for page in [1..pagesToReturn]
                            if selectedCountry is 'Canada'
                                url = "http://www.amazon.ca/s/ref=nb_sb_noss_2?url=node%3D3341338011&field-keywords=" + (phrase.split(' ').join('+')) + "&page=" + page;
                            else if selectedCountry is 'UK'
                                url = "http://www.amazon.co.uk/s/ref=sr_nr_n_6?rh=n%3A340831031%2Cn%3A430485031%2Ck%3Ahp&keywords=" + (phrase.split(' ').join('+')) + "&page=" + page;
                            else
                                url = "http://www.amazon.com/s/?rh=n:720576&field-keywords=" + (phrase.split(' ').join('+')) + "&page=" + page;

                            console.log(numRequestsToMake)
                            console.log(url)
                            _get(url).then(
                                (succ_data) ->
                                    numRequestsReturned += 1
                                    topContext.set('percentOfPagesFetched', (numRequestsReturned / numRequestsToMake) * 100)

                                    console.log(numRequestsReturned + ' ' + numRequestsToMake)
                                    requestDataToReturn.push(succ_data)
                                    if numRequestsReturned is numRequestsToMake
                                        resolve(requestDataToReturn)
                                    console.log('SUCCESS')
                                    return succ_data
                                (err_data) ->
                                    numRequestsReturned += 1
                                    topContext.set('percentOfPagesFetched', (numRequestsReturned / numRequestsToMake) * 100)

                                    if numRequestsReturned is numRequestsToMake
                                        resolve(requestDataToReturn)
                                    console.log('ERROR')
                                    return err_data
                            )
            )

            amazon_requests_promise.then(
                (responseList) ->
                    # Process the results here.
                    _parseResponses(responseList)
            ).then(
                (finalCleanedList) ->
                    topContext.set('finalCleanedList', finalCleanedList)
            )
        )
)

`export default InquiryController`