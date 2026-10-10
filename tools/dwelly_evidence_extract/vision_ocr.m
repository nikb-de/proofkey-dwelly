#import <Foundation/Foundation.h>
#import <Vision/Vision.h>

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 2) return 2;
        NSURL *url = [NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[1]]];
        VNRecognizeTextRequest *request = [[VNRecognizeTextRequest alloc] init];
        request.recognitionLevel = VNRequestTextRecognitionLevelAccurate;
        request.usesLanguageCorrection = NO;
        if (@available(macOS 13.0, *)) request.automaticallyDetectsLanguage = YES;
        VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithURL:url options:@{}];
        NSError *error = nil;
        if (![handler performRequests:@[request] error:&error]) {
            fputs("ocr_failed\n", stderr);
            return 1;
        }
        NSMutableArray *observations = [NSMutableArray array];
        NSMutableArray *lines = [NSMutableArray array];
        for (VNRecognizedTextObservation *item in request.results) {
            VNRecognizedText *candidate = [[item topCandidates:1] firstObject];
            if (candidate == nil) continue;
            CGRect box = item.boundingBox;
            [lines addObject:candidate.string];
            [observations addObject:@{
                @"text": candidate.string, @"confidence": @(candidate.confidence),
                @"box": @{@"x": @(box.origin.x), @"y": @(box.origin.y),
                          @"width": @(box.size.width), @"height": @(box.size.height)}
            }];
        }
        NSDictionary *result = @{
            @"extractor": @"Apple Vision VNRecognizeTextRequest accurate; language correction disabled",
            @"qualification": @"unverified_ocr_visible_text_only",
            @"text": [[lines componentsJoinedByString:@"\n"] stringByAppendingString:@"\n"],
            @"coordinateSystem": @"normalized_bottom_left_origin",
            @"requestRevision": @(request.revision), @"observations": observations
        };
        NSData *json = [NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingPrettyPrinted error:&error];
        if (json == nil) return 1;
        [[NSFileHandle fileHandleWithStandardOutput] writeData:json];
    }
    return 0;
}
