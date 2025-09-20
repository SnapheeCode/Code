"""Тексты GraphQL запросов/мутаций.

Примечание: схема может изменяться. При ошибках в production — проверьте актуальные
запросы в инструментах разработчика браузера (Network, вкладка graphql) и обновите строки ниже.
"""

# Справочники (типы работ, категории и т.п.)
GET_DICTIONARY = """
query getDictionary {
  dictionarylist {
    worktypes { id name count }
    workcategoriesgroup { name items { id name count } }
    phonemasks { maskId code mask country }
  }
}
"""


# Профиль (шаблоны, статусы)
GET_PROFILE = """
query getProfile {
  profile {
    id
    nickName
    role
    balance
    chatEnabled
    templates { id title text }
  }
}
"""


# Получение ленты аукциона по фильтрам/ограничениям (по мотивам HAR)
GET_AUCTION_WITH_CONSTRAINTS = """
query GetAuctionWithConstraints($skip: Int, $limit: Int, $filter: AuctionFilterInputType, $constraintsFilter: AuctionFilterInputType, $pagination: AuctionPaginationInputType) {
  auctionFilterConstraint(filter: $constraintsFilter) {
    minCountBid
    maxCountBid
    minUniqueValue
    maxUniqueValue
    minDeadline
    maxDeadline
    minBudget
    maxBudget
    __typename
  }
  auctionFilteredCount(filter: $filter)
  orders(skip: $skip, limit: $limit, filter: $filter, pagination: $pagination) {
    total
    captcha
    pages
    orders {
      ...orderDataFragment
      __typename
    }
    __typename
  }
  recommendedOrdersForExpert(limit: $limit) {
    orders {
      ...orderDataFragment
      __typename
    }
    __typename
  }
}

fragment orderDataFragment on order {
  id
  type { id name __typename }
  category { id name __typename }
  customer { id isOnline isTelegramEnabled nickName __typename }
  badges { id name __typename }
  title
  description
  budget
  recommendedBudget
  isFavorite
  isConsult
  isInviteOrder
  isPremium
  isHidden
  isPaid
  isRead
  creation
  deadline
  customerFiles { id name path hash sizeInMb readableCreationUnixtime type __typename }
  authorFiles { id __typename }
  countOffers
  isMatchFilter
  isMatchQualification
  authorHasOffer
  isExpressOrder
  authorOffer { id origin_bid bid text __typename }
  __typename
}
"""


# Детали для отклика (минимально необходимые поля)
GET_ORDER_FOR_BID = """
query getOrderForBid($id: ID!) {
  getOrderForBid(id: $id) {
    id
    budget
    recommendedBudget
    countOffers
  }
}
"""


# Мутация отправки отклика
MAKE_OFFER = """
mutation makeOffer($orderId: ID!, $bid: Int!, $message: String!, $expired: Int, $subscribe: Boolean) {
  makeOffer(orderId: $orderId, bid: $bid, text: $message, expired: $expired, subscribe: $subscribe) {
    id
    origin_bid
    bid
    text
    countOffersOfOrder
  }
}
"""


# Мутация отправки сообщения в диалог (название и поля предположительны; при интеграции — уточнить)
SEND_MESSAGE = """
mutation sendMessage($dialogId: ID!, $text: String!) {
  sendMessage(dialogId: $dialogId, text: $text) {
    id
    text
    createdAt
  }
}
"""

# Реальная мутация добавления комментария (сообщения) по заказу — по данным HAR
ADD_COMMENT = """
mutation addComment($orderId: ID!, $text: String!) {
  addComment(orderId: $orderId, text: $text) {
    __typename
    ...messageFragment
  }
}

fragment messageFragment on message {
  id
  user_id
  text
  creation
  isAdminComment
  isAutoHidden
  isRead
  watched
  files {
    id
    name
    hash
    type
    path
    sizeInMb
    isFinal
    __typename
  }
  __typename
}
"""
