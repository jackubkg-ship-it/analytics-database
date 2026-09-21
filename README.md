# analytics-database
Analitics for transport ussue and cost control on Azeri for small and large companies
İSTİFADƏÇİ TƏLİMATI
Texnikanın tmir bazasıə
Proqramdan istifadə qaydası: qoşulma, daxil olma və əsas imkanlar
Sentyabr 2026
1. Tlimatın tyinatıəə
Bu təlimat “Texnikanın təmir bazası” proqramından istifadə edəcək işçilər üçün hazırlanıb. Burada proqrama qoşulma, sistemə daxil olma, məlumatlara baxış və tez-tez rast gəlinən problemlərin həlli izah edilir.
Texnikanın təmir bazası – nəqliyyat vasitələri və texnikanın servis (təmir) qeydlərinin vahid yerdə toplandığı və təhlil edildiyi veb proqramdır. Proqram brauzer vasitəsilə açılır, əlavə proqram quraşdırmaq lazım deyil.
2. Proqramın imkanları
•
Podratçılar üzrə təmir və servis qeydlərinin vahid bazada saxlanılması;
•
Ehtiyat hissələrinin, görülən işlərin və yekun xərcin göstərilməsi;
•
Xərclərin və təmir tarixçəsinin cədvəl və qrafiklərlə təhlili;
•
Texnikanın planlı texniki xidmət (TO) vəziyyətinə nəzarət;
•
Kompüter və telefon brauzerindən istifadə imkanı.
3. Proqrama qoşulma
3.1. Tlblrəəə
•
Kompüter və ya telefon şirkət şəbəkəsinə qoşulu olmalıdır (Wi-Fi, kabel və ya VPN);
•
Müasir brauzer: Google Chrome, Microsoft Edge və ya Mozilla Firefox.
3.2. Qoşulma addımları
1.
Brauzeri açın.
2.
Ünvan sətrinə (axtarış sətrinə yox) proqramın ünvanını yazın: http://10.1.6.222:8000 və Enter düyməsini basın.
3.
Giriş səhifəsi açılacaq. Növbəti bölmədəki məlumatlarla daxil olun.
Diqqət: IP ünvan dəyişə bilər
Proqram işləyən kompüterə şəbəkə ünvanı dinamik (avtomatik) verildiyi üçün IP ünvan dəyişə bilər. Yuxarıda göstərilən ünvan hazırda müvəqqəti olaraq istifadə olunur. Səhifə açılmazsa, 5-ci bölməyə baxın.
Məsləhət: ünvanı brauzerdə əlfəcinə (bookmark) əlavə edin ki, hər dəfə yazmayasınız.
Səhifə 1 / 4
Texnikanın təmir bazası · İstifadəçi təlimatı
4. Sistem daxil olmaə
Hazırda proqramda müvəqqəti istifadəçi hesabı mövcuddur:
Məlumat
Dəyər
Proqramın ünvanı
http://<IP>:8000 (dəyişə bilər)
İstifadəçi adı
admin
Parol
admin
1.
Brauzerdə proqramın ünvanını açın.
2.
İstifadəçi adı sahəsinə user, parol sahəsinə user123 yazın.
3.
Giriş düyməsini basın – proqramın əsas səhifəsi açılacaq.
Müvəqqəti hesab
Bu hesab müvəqqətidir və sonradan dəyişdirilə bilər. Giriş məlumatlarını üçüncü şəxslərə verməyin.
5. IP ünvan dyişrs n etmli?əəəəə
Proqram işləyən kompüterə şəbəkə ünvanı avtomatik (dinamik) verilir. Kompüter yenidən qoşulanda və ya şəbəkə yenidən başlayanda IP ünvanın rəqəmləri dəyişə bilər. Ünvanın sonundakı :8000 hissəsi adətən qalır.
Səhifə açılmırsa:
1.
Kompüterin və ya telefonun şəbəkəyə (Wi-Fi, kabel, VPN) qoşulu olduğunu yoxlayın.
2.
Ünvanı düzgün yazdığınızdan əmin olun (http:// ilə başlamalı, sonunda :8000 olmalıdır).
3.
Sistem administratorundan cari IP ünvanı öyrənin.
4.
Yeni ünvanı http://IP-ünvan:8000 formatında yazın və əlfəcinə əlavə edin.
6. Proqramdakı mlumatlarə
Hər təmir (servis) qeydi aşağıdakı məlumatlar əsasında saxlanılır:
Sahə
Mənası
Avtomobilin markası
Nəqliyyat vasitəsinin və ya texnikanın markası
Dövlət qeydiyyat nişanı
Avtomobilin nömrə nişanı (məsələn, 77-AL-921)
Buraxılış ili
Texnikanın istehsal ili
Spidometr göstəricisi
Servisə daxil olarkən yürüş göstəricisi
Servisə daxil olan tarix
Texnikanın servisə qəbul edildiyi tarix
Servisdən planlaşdırılan çıxma tarixi
Təmirin bitməsi gözlənilən tarix
Servisdən faktiki çıxma tarixi
Texnikanın servisdən real çıxdığı tarix
Səhifə 2 / 4
Texnikanın təmir bazası · İstifadəçi təlimatı
Sahə Mənası
Sürücünün adı
Texnikanı idarə edən sürücü
Sorğunu göndərən şəxs
Təmir üçün sorğu göndərən şəxs
Təmiri təsdiqləyən şəxs
Sahədə təmiri təsdiqləyən şəxs(lər)
Dəyişdirilən ehtiyat hissəsi
Təmirdə dəyişdirilən hissələrin adı (bir qeyddə bir neçə hissə ola bilər)
Ehtiyat hissəsinin qiyməti
Hissələrin qiyməti («vahid qiymət × say = məbləğ» şəklində ola bilər)
Görülən işin qiyməti
İş haqqı (eyni formatda bir neçə iş ola bilər)
Təmirin qısa təsviri
Görülən işin qısa izahı
7. Xrcin hesablanmasıə
Yekun xərc aşağıdakı ardıcıllıqla formalaşır:
1.
Cəmi = ehtiyat hissəsinin qiyməti + görülən işin qiyməti;
2.
Əlavə faiz (15% və ya 20%) yalnız ehtiyat hissələrinin dəyərinə tətbiq olunur;
3.
Toplam xərc = Cəmi + əlavə faiz məbləği.
Nümunə (illustrativ rəqəmlər):
Hesablama
Nəticə
Ehtiyat hissəsi 200 + görülən iş 80
Cəmi = 280
Faiz 15%: 200 × 15%
30
Cəmi + faiz məbləği: 280 + 30
Toplam xərc = 310
8. Mlumatlara baxış v thliləəə
1.
Dövrü seçin: baxmaq istədiyiniz ayı və ya ili seçin.
2.
Axtarın və süzün: podratçı, avtomobilin dövlət nişanı və ya tarix üzrə axtarış və filtrdən istifadə edin.
3.
Nəticəni izləyin: cədvəl və qrafiklərdə təmirlərin sayını və xərcləri müqayisə edin.
Hesabın rolu
Hesabın rolundan asılı olaraq bəzi bölmələr (tam məlumat cədvəlləri və ya yalnız qrafiklər) görünə bilər. Lazım olan bölmə görünmürsə, administratora müraciət edin.
9. Texniki xidmt (TO) moduluə
Modul texnikanın planlı texniki xidmətinə vaxtında nəzarət etmək üçündür və üç hissədən ibarətdir:
•
Reqlamentlər – hər texnika üçün texniki xidmət növləri və dövrləri;
Səhifə 3 / 4
Texnikanın təmir bazası · İstifadəçi təlimatı
•
İstismar uçotu – texnikanın işləmə göstəriciləri (məsələn, yürüş);
•
Vəziyyət lövhəsi – hansı texnikanın xidmət vaxtının çatdığı və ya gecikdiyi.
10. Telefondan istifadə
Proqramın mobil veb versiyası da mövcuddur:
1.
Telefonu şirkət Wi-Fi şəbəkəsinə qoşun.
2.
Telefonun brauzerini açın (Chrome, Safari).
3.
Proqramın ünvanını yazın və istifadəçi adı ilə parolla daxil olun.
Ünvan dəyişərsə, 5-ci bölmədəki addımlara baxın.
11. Thlüksizlik qaydalarıəə
•
Giriş məlumatlarını (parolu) üçüncü şəxslərə verməyin;
•
Ortaq kompüterlərdə brauzerin “parolu yadda saxla” təklifini qəbul etməyin;
•
İşi bitirdikdən sonra proqramdan çıxış edin;
•
Gözlənilməz xəta və ya şübhəli fəaliyyət görsəniz, sistem administratoruna məlumat verin.
12. Problemlrin hlliəə
Problem
Mümkün səbəb
Nə etməli
Səhifə açılmır
IP ünvan dəyişib və ya şəbəkəyə qoşulu deyilsiniz
Şəbəkə qoşulmasını yoxlayın, administratordan cari ünvanı öyrənin (5-ci bölmə)
Daxil olmaq mümkün olmur
İstifadəçi adı və ya parol səhv yazılıb
Caps Lock və klaviatura dilini yoxlayın, məlumatları yenidən daxil edin
Bölmə və ya məlumat görünmür
Hesabın icazələri məhduddur
Administratora müraciət edin
Səhifə yavaş açılır
Şəbəkə yükü və ya müvəqqəti xəta
Səhifəni yeniləyin (F5), bir az sonra yenidən cəhd edin
13. laqƏə
Proqramla bağlı suallar, yeni hesab sorğusu və ya texniki problemlər üçün sistem administratoruna müraciət edin.
